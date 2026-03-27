import xml.etree.ElementTree as ET

def canonicalize_xml(xml_string):
    """
    Returns a canonical string representation of an XML document.
    Ignores whitespace differences and attribute ordering.
    """
    try:
        return ET.canonicalize(xml_string, strip_text=True)
    except Exception as e:
        print(f"Warning: XML parsing failed for comparison - {e}")
        return xml_string.strip()

def compare_bpmn(bpmn_xml_1, bpmn_xml_2):
    """
    Compares two BPMN XML strings.
    Returns True if they are functionally identical.
    """
    canon1 = canonicalize_xml(bpmn_xml_1)
    canon2 = canonicalize_xml(bpmn_xml_2)
    return canon1 == canon2
