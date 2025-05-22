import json
import xml.etree.ElementTree as ET
from pulsar import Function

class XMLToJSONFunction(Function):
    def __init__(self):
        pass

    def process(self, input_xml_string, context):
        logger = context.get_logger()
        logger.info(f"Received input: '{input_xml_string[:100]}...'") # Log snippet

        try:
            # Parse XML
            # A more robust solution might involve a schema or more complex parsing logic
            root = ET.fromstring(input_xml_string)
            
            # Basic transformation: convert XML elements to a dictionary
            # This is a simplified example. Real-world XML might need more sophisticated handling,
            # especially for nested elements, attributes, lists, etc.
            
            data_dict = {}
            for child in root:
                # If element has children, recursively process them (simplified)
                if len(list(child)) > 0:
                    data_dict[child.tag] = self._parse_element(child)
                else:
                    data_dict[child.tag] = child.text
            
            # Convert dictionary to JSON string
            output_json_string = json.dumps(data_dict)
            logger.info(f"Successfully transformed to JSON: '{output_json_string[:100]}...'")
            
            return output_json_string

        except ET.ParseError as e:
            logger.error(f"XML Parsing Error: {e}. Input: {input_xml_string}")
            # Decide how to handle errors:
            # - Return None (message won't be sent to output topic)
            # - Publish to a dead-letter topic (DLQ)
            # - Raise an exception (function will be marked as failed, message might be retried)
            return None 
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}. Input: {input_xml_string}")
            return None

    def _parse_element(self, element):
        """ Helper function to parse an XML element and its children into a dict. """
        parsed = {}
        # Include attributes if any
        if element.attrib:
            # Prefix attributes to avoid collision with child tags, or handle as needed
            for k, v in element.attrib.items():
                parsed[f"@{k}"] = v

        for child in element:
            if len(list(child)) > 0: # Nested element
                if child.tag in parsed: # Handle multiple elements with the same tag (list)
                    if not isinstance(parsed[child.tag], list):
                        parsed[child.tag] = [parsed[child.tag]] # Convert to list
                    parsed[child.tag].append(self._parse_element(child))
                else:
                    parsed[child.tag] = self._parse_element(child)
            else: # Simple text element
                if child.tag in parsed: # Handle multiple elements with the same tag (list)
                     if not isinstance(parsed[child.tag], list):
                        parsed[child.tag] = [parsed[child.tag]] # Convert to list
                     parsed[child.tag].append(child.text)
                else:
                    parsed[child.tag] = child.text
        
        # If element has no children and no attributes but has text, return the text
        if not parsed and element.text and element.text.strip():
            return element.text.strip()
            
        return parsed


# Example usage (for local testing, not part of Pulsar Function execution)
if __name__ == '__main__':
    # This part is for local testing and will not be executed by Pulsar.
    class MockContext:
        def get_logger(self):
            import logging
            logging.basicConfig(level=logging.INFO)
            return logging.getLogger("XMLToJSONFunctionTest")

    test_func = XMLToJSONFunction()
    mock_context = MockContext()
    
    sample_xml_1 = """
    <event>
        <id>evt-001</id>
        <timestamp>2023-01-01T12:00:00Z</timestamp>
        <payload>
            <value1>Data A</value1>
            <value2>123.45</value2>
        </payload>
        <meta key="source">test</meta>
    </event>
    """
    
    sample_xml_2 = """
    <order>
        <order_id>ORD-002</order_id>
        <customer_id>CUST-100</customer_id>
        <items>
            <item sku="SKU001" quantity="2">
                <name>Product A</name>
                <price>10.00</price>
            </item>
            <item sku="SKU002" quantity="1">
                <name>Product B</name>
                <price>25.50</price>
            </item>
        </items>
        <total>45.50</total>
    </order>
    """

    malformed_xml = "<event><id>test</id><payload>missing closing tag</payload"

    print("--- Test Case 1: Simple Event ---")
    json_output_1 = test_func.process(sample_xml_1.strip(), mock_context)
    print(f"Input XML:\n{sample_xml_1}")
    print(f"Output JSON:\n{json.dumps(json.loads(json_output_1), indent=2) if json_output_1 else 'None'}\n")

    print("--- Test Case 2: Nested Order ---")
    json_output_2 = test_func.process(sample_xml_2.strip(), mock_context)
    print(f"Input XML:\n{sample_xml_2}")
    print(f"Output JSON:\n{json.dumps(json.loads(json_output_2), indent=2) if json_output_2 else 'None'}\n")

    print("--- Test Case 3: Malformed XML ---")
    json_output_3 = test_func.process(malformed_xml.strip(), mock_context)
    print(f"Input XML:\n{malformed_xml}")
    print(f"Output JSON:\n{json_output_3}\n")