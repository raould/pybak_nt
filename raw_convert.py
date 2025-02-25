import os

def raw_convert( src_file, dst_file ):
    # convert was slow.
    # subprocess.check_output( [ 'convert', src_file, dst_file ] )
    result = os.system( 'dcraw -c %s | cjpeg -quality 80 > %s' % ( src_file, dst_file ) )
    status = (result >> 8)
    return status == 0

