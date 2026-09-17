"""Compare two kicad-cli XML netlists by pin grouping (net names and codes ignored).

Usage: python net_diff.py before.xml after.xml [ref-prefix ...]
Prints every net (as its set of (ref,pin) nodes) that exists in one file and not the other, restricted to nets
touching a ref that starts with one of the given prefixes (default: all).  #PWR / #FLG symbols are ignored.
A net is printed with its name in each file for orientation.
"""
import sys
import xml.etree.ElementTree as ET


def load(path):
    root = ET.parse(path).getroot()
    nets = {}
    for net in root.iter("net"):
        nodes = frozenset((n.get("ref"), n.get("pin")) for n in net.findall("node") if not n.get("ref", "").startswith("#"))
        if nodes:
            nets[nodes] = net.get("name")
    return nets


def main():
    a, b = load(sys.argv[1]), load(sys.argv[2])
    prefixes = tuple(sys.argv[3:])

    def keep(nodes):
        return not prefixes or any(ref.startswith(prefixes) for ref, _ in nodes)

    only_a = [n for n in a if n not in b and keep(n)]
    only_b = [n for n in b if n not in a and keep(n)]

    def fmt(nodes):
        return " ".join("%s.%s" % rp for rp in sorted(nodes))

    print("nets only in %s: %d" % (sys.argv[1], len(only_a)))
    for n in sorted(only_a, key=lambda s: sorted(s)):
        print("  - [%s] %s" % (a[n], fmt(n)))
    print("nets only in %s: %d" % (sys.argv[2], len(only_b)))
    for n in sorted(only_b, key=lambda s: sorted(s)):
        print("  + [%s] %s" % (b[n], fmt(n)))
    sys.exit(1 if (only_a or only_b) else 0)


if __name__ == "__main__":
    main()
