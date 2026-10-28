#portapy_pragma ALLOW_MODULE
import pk_types as pk

# path_list: a PkOsPath (a list of names, root first). N: the naming strategy
# (pk.PkNamingP), so the '_' and '.' separators are the same type as the names.

def get_checksum_from_path_list( path_list, N ):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkNamingP[pk.PkOsName]) -> pk.PkOptional[pk.PkOsName]
    parts = N.split_name( path_list[-1], '_' )
    if len(parts) != 2 or len(parts[0]) != 32:
        return None
    else:
        return parts[0]

def get_length_from_path_list( path_list, N ):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkNamingP[pk.PkOsName]) -> pk.PkOptional[pk.PkOsName]
    parts = N.split_name( path_list[-1], '_' )
    if len(parts) != 2:
        return None
    else:
        # [0] to remove metadata extensions.
        return N.split_name( parts[1], '.' )[0]
