"""Read the KiCad XML netlist exported by `kicad-cli sch export netlist --format kicadxml`."""
import xml.etree.ElementTree as ET


class Comp:
    def __init__(self, el):
        self.ref = el.get("ref")
        self.value = el.findtext("value", "")
        self.footprint = el.findtext("footprint", "")
        self.datasheet = el.findtext("datasheet", "")
        self.description = el.findtext("description", "")
        self.fields = {}
        for f in el.findall("./fields/field"):
            if f.get("name") not in ("Footprint", "Datasheet", "Description"):
                self.fields[f.get("name")] = f.text or ""
        self.props = {p.get("name"): p.get("value") for p in el.findall("property")}
        sp = el.find("sheetpath")
        self.sheetname = sp.get("names") if sp is not None else "/"
        sheet_tstamps = sp.get("tstamps") if sp is not None else "/"
        self.tstamp = el.findtext("tstamps", "")
        self.path = sheet_tstamps.rstrip("/") + "/" + self.tstamp
        self.sheetfile = self.props.get("Sheetfile", "")
        self.dnp = "dnp" in self.props
        self.in_bom = "exclude_from_bom" not in self.props
        self.block = self.fields.get("Block", "")
        self.lcsc = self.fields.get("LCSC", "")


def read(path):
    root = ET.parse(path).getroot()
    comps = {}
    for el in root.findall("./components/comp"):
        c = Comp(el)
        comps[c.ref] = c
    nets = {}            # name -> list of (ref, pin)
    pad_net = {}         # (ref, pin) -> net name
    for n in root.findall("./nets/net"):
        name = n.get("name")
        nodes = [(nd.get("ref"), nd.get("pin")) for nd in n.findall("node")]
        nets[name] = nodes
        for ref, pin in nodes:
            pad_net[(ref, pin)] = name
    return comps, nets, pad_net
