# Pulsar Local Iteration 1

## Phase 3: Pulsar Function for Transformation

### Deploying the XML-to-JSON Pulsar Function

The Pulsar Function `xml_to_json.py` transforms XML messages from an input topic to JSON messages on an output topic.

1.  **Ensure Pulsar is running:**
    ```bash
    docker-compose up -d pulsar
    ```

2.  **Copy the function to the Pulsar container:**
    The Pulsar Function needs to be accessible from within the Pulsar container. You can copy it directly:
    ```bash
    docker cp pulsar_functions/xml_to_json_transformer/xml_to_json.py pulsar-standalone:/pulsar/
    # If you have requirements, also copy requirements.txt and use --user-config '{"dependenciesPath": "/pulsar/requirements.txt"}' or similar
    # For this example, requirements.txt is empty, so we can omit it or copy an empty one.
    docker cp pulsar_functions/xml_to_json_transformer/requirements.txt pulsar-standalone:/pulsar/
    ```
    *Note: For more robust deployments, especially with dependencies, packaging the function as a NAR file or using `--url` with a file accessible via HTTP is recommended. For this local iteration, direct copy is simpler.*

3.  **Deploy the function using `pulsar-admin`:**
    Execute the following command from your host machine, or run it inside the Pulsar container's shell.
    The topics are defined in your `.env` file (e.g., `RAW_XML_TOPIC` and `TRANSFORMED_JSON_TOPIC`).

    ```bash
    docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin functions create \
      --py /pulsar/xml_to_json.py \
      --classname xml_to_json.XMLToJSONFunction \
      --inputs "$(grep RAW_XML_TOPIC .env | cut -d '=' -f2)" \
      --output "$(grep TRANSFORMED_JSON_TOPIC .env | cut -d '=' -f2)" \
      --name xml-to-json-transformer \
      --tenant public \
      --namespace default \
      --parallelism 1
      # Add --user-config '{"dependenciesPath": "/pulsar/requirements.txt"}' if you have dependencies
    ```
    *Explanation of parameters:*
    *   `--py /pulsar/xml_to_json.py`: Path to the Python function file *inside* the Pulsar container.
    *   `--classname xml_to_json.XMLToJSONFunction`: The class name of your function.
    *   `--inputs`: The topic from which the function will consume messages.
    *   `--output`: The topic to which the function will send transformed messages.
    *   `--name`: A unique name for your function.
    *   `--tenant public --namespace default`: The default tenant and namespace.

4.  **Verify function deployment:**
    Check the status of the function:
    ```bash
    docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin functions status --name xml-to-json-transformer --tenant public --namespace default
    ```
    You should see `"running": true` among other details.

    Check the logs of the function if needed:
    ```bash
    docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin functions logs --name xml-to-json-transformer --tenant public --namespace default
    # Or, for live logs:
    # docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin functions logs --name xml-to-json-transformer --tenant public --namespace default -f
    ```

## Phase 4: Pulsar Kinesis IO Connector Configuration & Deployment

### Deploying the Kinesis Source Connector

The Pulsar Kinesis Source Connector ingests data from an AWS Kinesis stream (simulated by LocalStack) into a Pulsar topic.

1.  **Ensure Pulsar and LocalStack are running:**
    ```bash
    docker-compose up -d pulsar localstack
    ```

2.  **Create the Kinesis Stream in LocalStack (if not already created):**
    You'll need the AWS CLI installed on your host, or you can run this from a container that has it.
    ```bash
    aws --endpoint-url=http://localhost:4566 kinesis create-stream --stream-name "$(grep KINESIS_STREAM_NAME .env | cut -d '=' -f2)" --shard-count 1
    ```
    *Note: If the stream already exists, this command will give an error, which can be ignored in that case.*

3.  **Download the Kinesis Source Connector NAR file:**
    The connector version should ideally match your Pulsar version. For Pulsar 3.1.2, the connector might be `pulsar-io-kinesis-3.1.2.nar`.
    You can find official connectors on the Apache Pulsar downloads page or Pulsar Hub.
    For this example, let's assume you've downloaded `pulsar-io-kinesis-3.1.2.nar` and placed it in a `./connectors` directory in your project root (create this directory if it doesn't exist).
    ```bash
    # Example:
    mkdir -p ./connectors
    # wget -O ./connectors/pulsar-io-kinesis-3.1.2.nar <URL_TO_NAR_FILE> 
    # Replace <URL_TO_NAR_FILE> with the actual download link.
    # As a placeholder if you don't have the URL handy for the subtask,
    # the user will need to manually download it.
    echo "Please download pulsar-io-kinesis-3.1.2.nar (or compatible version) and place it in ./connectors/"
    ```

4.  **Copy the connector NAR file and its configuration to the Pulsar container:**
    ```bash
    docker cp ./connectors/pulsar-io-kinesis-3.1.2.nar pulsar-standalone:/pulsar/connectors/
    docker cp ./connector_configs/kinesis-source-config.yml pulsar-standalone:/pulsar/
    ```
    *Make sure the NAR file name in the command matches the one you downloaded.*
    *The target directory `/pulsar/connectors/` is a common location for connectors in Pulsar Docker images.*

5.  **Deploy the Kinesis Source Connector using `pulsar-admin`:**
    The destination topic is defined in your `.env` file (e.g., `RAW_XML_TOPIC`).
    ```bash
    docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin sources create \
      --archive /pulsar/connectors/pulsar-io-kinesis-3.1.2.nar \
      --source-config-file /pulsar/kinesis-source-config.yml \
      --name kinesis-xml-source \
      --destination-topic-name "$(grep RAW_XML_TOPIC .env | cut -d '=' -f2)" \
      --parallelism 1 \
      --tenant public \
      --namespace default
    ```

6.  **Verify connector deployment:**
    Check the status of the source:
    ```bash
    docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin sources status --name kinesis-xml-source --tenant public --namespace default
    ```
    You should see `"running": true`. If not, check the logs for errors.

    Check the logs of the connector:
    ```bash
    docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin sources logs --name kinesis-xml-source --tenant public --namespace default
    ```
## Phase 5: Pipeline Assembly & Manual Verification

### Create Necessary Pulsar Topics

While Pulsar can auto-create topics, it's good practice to create them explicitly for your pipeline. The topics are defined in your `.env` file.

1.  **Ensure Pulsar is running:**
    ```bash
    docker-compose up -d pulsar
    ```

2.  **Create the raw XML input topic:**
    This topic will receive data from the Kinesis source connector.
    ```bash
    docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin topics create-partitioned-topic -p 1 "$(grep RAW_XML_TOPIC .env | cut -d '=' -f2)"
    # Or for a non-partitioned topic:
    # docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin topics create "$(grep RAW_XML_TOPIC .env | cut -d '=' -f2)"
    ```
    *Using a partitioned topic with 1 partition for now, as it's a common default. Adjust partitions as needed.*

3.  **Create the transformed JSON output topic:**
    This topic will receive data from the XML-to-JSON Pulsar Function.
    ```bash
    docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin topics create-partitioned-topic -p 1 "$(grep TRANSFORMED_JSON_TOPIC .env | cut -d '=' -f2)"
    # Or for a non-partitioned topic:
    # docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin topics create "$(grep TRANSFORMED_JSON_TOPIC .env | cut -d '=' -f2)"
    ```

4.  **Verify topics (optional):**
    List topics in the `public/default` namespace:
    ```bash
    docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin topics list public/default
    ```
    You should see your newly created topics in the list.

### Manually Test End-to-End Data Flow

This section describes how to manually verify that data flows from the Kinesis producer, through the Kinesis Source Connector, is transformed by the Pulsar Function, and finally arrives in the output topic.

**Prerequisites:**
*   Docker environment is up: `docker-compose up -d pulsar localstack`
*   Kinesis stream `$(grep KINESIS_STREAM_NAME .env | cut -d '=' -f2)` is created in LocalStack.
*   Pulsar topics `$(grep RAW_XML_TOPIC .env | cut -d '=' -f2)` and `$(grep TRANSFORMED_JSON_TOPIC .env | cut -d '=' -f2)` are created.
*   Kinesis Source Connector `kinesis-xml-source` is deployed and running.
*   Pulsar Function `xml-to-json-transformer` is deployed and running.

**Steps:**

1.  **Start a Pulsar consumer on the final output topic (`TRANSFORMED_JSON_TOPIC`):**
    Open a new terminal window and run the following command. This will listen for messages on the topic where JSON data should appear.
    ```bash
    docker exec -it pulsar-standalone /pulsar/bin/pulsar-client consume -s "manual-test-sub" -n 0 "$(grep TRANSFORMED_JSON_TOPIC .env | cut -d '=' -f2)" -p Earliest
    ```
    Keep this terminal open and visible.

2.  **Run the Kinesis XML Data Producer:**
    Open another terminal window. Navigate to the `pulsar-local-iteration1` directory.
    Make sure your Python environment has `boto3` installed (from `data_generators/requirements.txt`).
    If you are using the default endpoint in the script (`http://localhost:4566`), ensure LocalStack's port 4566 is mapped correctly in `docker-compose.yml` and accessible from where you run the script.

    Run the producer script to send a few messages:
    ```bash
    # Ensure you are in the pulsar-local-iteration1 directory
    # If you have a virtual environment, activate it: source venv/bin/activate
    python data_generators/kinesis_xml_producer.py --num-messages 5 --delay 1 --endpoint-url http://localhost:4566
    ```
    *   `--num-messages 5`: Sends 5 messages.
    *   `--delay 1`: Sends one message per second.
    *   `--endpoint-url http://localhost:4566`: Explicitly point to LocalStack on the host.

3.  **Observe the Consumer Output:**
    Switch back to the terminal where the Pulsar consumer is running.
    You should see the transformed JSON messages appearing. For example:
    ```
    ----- MSG ID -----
    persistent://public/default/transformed-json-data/...
    ----- PROPERTIES -----
    null
    ----- PAYLOAD -----
    {"id": "...", "source": "kinesis_xml_producer", "timestamp": "...", "payload": {"value1": "...", "value2": "..."}}
    ```
    Verify that the content matches the expected JSON transformation of the XML data sent by the producer.

4.  **Check Logs for Errors (Troubleshooting):**
    If you don't see messages or encounter issues:
    *   **Kinesis Producer Script:** Check its console output for any errors.
    *   **LocalStack Logs:**
        ```bash
        docker logs localstack
        ```
        Look for Kinesis related activity or errors.
    *   **Kinesis Source Connector Logs:**
        ```bash
        docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin sources logs --name kinesis-xml-source
        ```
    *   **XML-to-JSON Pulsar Function Logs:**
        ```bash
        docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin functions logs --name xml-to-json-transformer
        ```
    *   **Pulsar Broker Logs:**
        ```bash
        docker logs pulsar-standalone
        ```
        Look for any general Pulsar errors.

This manual test helps confirm that all components are connected and working as expected before moving to automated benchmarking.
## Phase 6: Monitoring & Logging Setup

### Accessing Pulsar Component Logs

Effective troubleshooting and monitoring require access to logs from various components.

1.  **Pulsar Broker Logs:**
    For Pulsar running in standalone mode via Docker Compose (container name `pulsar-standalone`):
    ```bash
    docker logs pulsar-standalone
    ```
    To follow logs live:
    ```bash
    docker logs -f pulsar-standalone
    ```
    Pulsar's detailed logs are typically within the container at `/pulsar/logs/`. You can access them via `docker exec` if needed.

2.  **Pulsar Function Worker Logs:**
    When running Pulsar in standalone mode, function worker logs are usually part of the main Pulsar broker logs:
    ```bash
    docker logs pulsar-standalone | grep FunctionWorker # Or similar filtering
    ```

3.  **Pulsar Function Logs (Specific Function):**
    To get logs for a specific deployed function (e.g., `xml-to-json-transformer`):
    ```bash
    docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin functions logs --name xml-to-json-transformer --tenant public --namespace default
    ```
    To follow logs live:
    ```bash
    docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin functions logs --name xml-to-json-transformer --tenant public --namespace default -f
    ```

4.  **Pulsar IO Connector Logs (Specific Connector):**
    To get logs for a specific deployed source or sink (e.g., `kinesis-xml-source`):
    ```bash
    docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin sources logs --name kinesis-xml-source --tenant public --namespace default
    ```
    To follow logs live:
    ```bash
    docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin sources logs --name kinesis-xml-source --tenant public --namespace default -f
    ```
    *(Use `sinks` instead of `sources` for sink connectors).*

5.  **LocalStack Logs:**
    For LocalStack (container name `localstack`):
    ```bash
    docker logs localstack
    ```
    To follow logs live:
    ```bash
    docker logs -f localstack
    ```
    These logs will show activity for simulated AWS services like Kinesis.

Remember to replace placeholder names like `xml-to-json-transformer` or `kinesis-xml-source` if you've used different names in your deployment commands.

### Accessing Pulsar Metrics

Pulsar exposes metrics that are crucial for understanding performance and operational health.

1.  **Prometheus Metrics Endpoint:**
    The `docker-compose.yml` configures Pulsar to expose Prometheus-compatible metrics on port `8081` (mapped to host port `8081`).
    You can access these metrics using `curl` or by pointing a Prometheus scraper to this endpoint:
    ```bash
    curl http://localhost:8081/metrics
    ```
    This will output a large text response with many metrics for the broker, topics, subscriptions, etc.

2.  **Pulsar Admin CLI for Stats:**
    The `pulsar-admin` tool provides commands to get specific stats.

    *   **Topic Stats:**
        ```bash
        # For a specific topic (e.g., your raw XML topic)
        docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin topics stats "$(grep RAW_XML_TOPIC .env | cut -d '=' -f2)"
        # For your transformed JSON topic
        docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin topics stats "$(grep TRANSFORMED_JSON_TOPIC .env | cut -d '=' -f2)"
        ```
        This shows message rates, storage size, subscriptions, etc.

    *   **Subscription Stats (Per Topic):**
        ```bash
        docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin topics stats-internal "$(grep RAW_XML_TOPIC .env | cut -d '=' -f2)"
        # Look for subscription specific details
        ```

    *   **Kinesis Source Connector Stats:**
        The `status` command for sources also includes metrics. The `--get-status-h` flag is mentioned in the issue but might be specific to certain connector types or Pulsar versions for detailed human-readable metrics. Standard status gives JSON.
        ```bash
        docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin sources status --name kinesis-xml-source --tenant public --namespace default
        ```
        This shows messages received, errors, etc.

    *   **Pulsar Function Stats:**
        ```bash
        docker exec -it pulsar-standalone /pulsar/bin/pulsar-admin functions stats --name xml-to-json-transformer --tenant public --namespace default
        ```
        This shows messages processed, errors, latency, etc.

3.  **Docker Container Stats:**
    For basic resource utilization (CPU, Memory) of the containers:
    ```bash
    docker stats pulsar-standalone localstack
    ```
    Press `Ctrl+C` to stop. For collecting this over time, you might redirect output to a file or use `docker stats --no-stream`.

These metrics are essential for the benchmarking phase.
