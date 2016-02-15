#!/usr/bin/env python
#
# A script to convert an .ovf virtual appliance definition
# into a format usable by a ScaleComputing cluster.

import sys
import argparse
import subprocess
import tempfile
import os
import os.path
import tarfile
import string
import uuid
import random

from bs4 import BeautifulSoup

import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('ovf2scale')

CONVERTER="qemu-img"
SCALE_XML_TEMPLATE="scalevm-template.xml"

DISK_TEMPLATE = """
    <disk type="network" device="disk">
      <boot order="1"/>
      <driver name="qemu" type="scribe" cache="writethrough" io="native"/>
      <source protocol="scribe" name="${diskname}"/>
      <target dev="${disk_dev}"/>
      <geometry cyls="16383" heads="16" secs="63" trans="lba"/>
    </disk>"""

INTERFACE_TEMPLATE = """
    <interface type="bridge">
      <mac address="$randmac"/>
      <model type="e1000"/>
      <link state="up"/>
      <source bridge="lan"/>
    </interface>"""

def convert_vm(args):
    """
    Convert an OVF formatted virtual machine definition to Scale format
    """
    ovffile = open(args.ovffile, "r").read()
    soup = BeautifulSoup(ovffile)

    # Find the name of the vm. The Scale cluster exports VM files into
    # an SMB share directory with the same name as the .xml file that
    # defines the VM structure.
    vm_name = soup.envelope.virtualsystem['ovf:id']

    vm_dir = "./%s" % vm_name
    if not os.path.isdir(vm_dir):
        os.mkdir(vm_dir)
    
    # Find the vmdk files to convert
    fileset = parse_file_references(soup)
    diskset = parse_disks(soup)

    # Now we reformat each of the vmdk files into qcow2 format
    filemap = {}

    disk_list = []
    basedir = os.path.dirname(args.ovffile)
    for i, diskfile in enumerate(fileset.values()):
        disk_spec = {}
        filepath = os.path.join(basedir, diskfile['ovf:href'])
        #log.debug("Filepath to convert: %s", filepath)
        newpath = vmdk_to_qcow2(filepath, vm_dir)
        filemap[filepath] = newpath

        scribename = os.path.splitext(os.path.basename(newpath))[0]
        #log.debug("scribename: %s", scribename)
        disk_spec['diskname'] = "scribe/%s" % scribename
        disk_spec['disk_dev'] = "hd" + string.lowercase[i+1]
        #log.debug("disk_dev is: %s", disk_spec['disk_dev'])
        disk_list.append(disk_spec)
        pass

    disk_tmpl = string.Template(DISK_TEMPLATE)
    iface_tmpl = string.Template(INTERFACE_TEMPLATE)
    
    tmpl = string.Template(open(SCALE_XML_TEMPLATE).read())

    disk_xml = '\n'.join([ disk_tmpl.substitute(x) for x in disk_list ])

    iface_xml = '\n'.join([iface_tmpl.substitute({'randmac': new_mac_addr()}) for x in soup.envelope.networksection.find_all('network')])
    
    result = tmpl.substitute({'vm_name': vm_name,
                              'vm_descr': "Testing conversion",
                              'vm_uuid': uuid.uuid4(),
                              'vm_ram': "2048",
                              'vm_vcpu': "1",
                              'qcow_disks': disk_xml,
                              'interfaces': iface_xml,
                          })
    #log.debug(result)
    # Write the new template file out to disk
    outfile = os.path.join(vm_dir, '%s.xml' % vm_name)
    ofd = open(outfile, 'w')
    ofd.write(result)
    ofd.close()

def parse_file_references(soup):
    """
    Parse a list of file references from the OVF file into a dictionary
    """
    fileset = {}
    for ref in soup.envelope.references.find_all('file'):
        fileset[ref['ovf:id']] = ref
        pass
    return fileset

def parse_disks(soup):
    """
    Parse disk from OVF
    """
    diskset = {}
    for disk in soup.envelope.disksection.find_all('disk'):
        diskset[disk['ovf:diskid']] = disk
        pass
    return diskset
    
def vmdk_to_qcow2(srcfile, destdir):
    """
    Convert a given filepath from vmdk format to qcow2 format
    """
    filename, extension = os.path.splitext(os.path.basename(srcfile))
    qcow2file = os.path.join(destdir, '.'.join([filename, 'qcow2']))
    log.debug("new filename: %s", qcow2file)
    # See if the file already exists. If not, convert it.
    if os.path.exists(qcow2file):
        log.info("qcow2 format file already exists. Skipping conversion...")
    else:
        #subprocess.check_call([CONVERTER, 'convert', '-O', 'qcow2', '-o', 'compat=0.10', srcfile, qcow2file])
        pass
    return(qcow2file)

def new_mac_addr():
    """Generate a new MAC address
    """
    mac = [ 0x7c, 0x4c, 0x58, # Scale Computing OUI
            random.randint(0x00, 0x7f),
            random.randint(0x00, 0xff),            
            random.randint(0x00, 0xff),
    ]
    return ':'.join(["%02x" % x for x in mac])
    
if __name__ == '__main__':

    ap = argparse.ArgumentParser(description="Convert OVF file to ScaleComputing format",
                             formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    ap.add_argument('-o', '--outfile', help="Optional filename for output")
    ap.add_argument('ovffile', help="OVF file to convert")
    
    args = ap.parse_args()

    convert_vm(args)
