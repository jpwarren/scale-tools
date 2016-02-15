# scale-tools
Tools for ScaleComputing clusters

Well, I say tools. More like _dodgy hacks that sort-of work_.

Use at your own risk of dismemberment and death.

## ovf2scale.py

This tool converts a .ovf formatted VM definition into one that can
be imported into a ScaleComputing cluster.

ScaleComputing uses KVM and qcow2 format disk files, and has its own
XML definition file that lives inside a directory named after the VM
for import/export. This tool parses the source .ovf and extracts the
barest of minimum information to make sense for the image import
structure.

It calls qemu-img to convert VMDK format images into .qcow2 images
ready for importing, and puts the appropriate path into the .xml file
so it will work. The qcow2 files are placed into the directory with the
XML file.

Put the resulting directory into an SMB accessible fileshare somewhere
(I use Samba) and the VM should import ok.

I've had plenty of success in getting images imported using this method,
but it's still pretty rough.
