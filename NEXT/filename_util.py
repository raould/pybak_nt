#portapy_pragma ALLOW_MODULE
import naming

name_kind, root_to_native, name_to_bytes, bytes_to_name = naming.choose_naming_T()
_UNDERSCORE = name_to_bytes('_')

def get_checksum_from_path( path ):
    parts = os.path.basename( path ).split(_UNDERSCORE)
    if len(parts) != 2 or len(parts[0]) != 32:
        return None
    else:
        return parts[0]

def get_length_from_path( path ):
    parts = os.path.basename( path ).split( "_" )
    if len(parts) != 2:
        return None 
    else:
        # [0] to remove metadata extensions.
        return parts[1].split(".")[0]
