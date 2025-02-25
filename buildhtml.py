#!/usr/bin/env python

# use like:
#  ./buildhtml.py /var/www/html/jces/tmp http://www.monad.com/jces/tmp pybak browse,
# then the urls inside generated htmls will be like:
#  http://www.monad.com/jces/tmp/browse/...
# and
#  http://www.monad.com/jces/tmp/pybak/...

import hexlpathutil
import sys
import traceback
import os
import os.path
import re
import stat
import shutil
import re
import util
import metadata
import urlfix
import urlparse
import visit_core
import exts
from PIL import Image
from PIL import ImageDraw
import rawpy
import imageio
import font
from datetime import datetime
import json
from s3upload import S3Upload
from s3upload import get_bucket_name

gThumbnailFileName = "000_thumbnails.html" # show up first in listings.
gThumbnailJSONFileName = "zzz_ignoreme.json" # show up last?!
THUMBNAIL_SIZE = 64
assert THUMBNAIL_SIZE < util.WEB_SIZE
IMAGE_BY_DATE_DIRNAME = "image_by_date"

g_font = None
g_sheet_htmlt = """<html>
<body>
<!-- title --><br>
<!-- mark -->
<!-- mark -->
</body>
</html>
"""

gCrawlEverything = "crawl_everything"
gCrawlImagesOnly = "crawl_images_only"
gCrawlNotImages = "crawl_not_images"

gExts = exts.getExts()
gRawExts = exts.getRawExts()

def get_unrooted_path( path ):
    path = os.path.normpath( path )
    return re.sub( "^" + os.path.sep, "", os.path.normpath(path) )

def get_html_parent_path( base, dst_root, host, host_path ):
    host_safe = re.sub( "/", "_", host )
    host_path_safe = get_unrooted_path( host_path )
    p = os.path.join(
        base,
        dst_root,
        host_safe,
        os.path.dirname( host_path_safe ) )
    #visit_core.logVars( locals() )
    return p

def ensure_dir_path( base, dst_root, host, host_path ):
    path = get_html_parent_path( base, dst_root, host, host_path )
    util.ensure_path( path )

def get_sym_path( path ):
    pdir, file = os.path.split( path )
    sym_path = os.path.join( pdir, ".syms", file )
    return sym_path

def build_aka( base, dst_root, urlize, host, host_path, html_path, md ):
    #visit_core.log()
    aka = []
    def aka_fn( _md, _host, _path, _pathData, _fnData ):
        # don't repeat the currently-generating html thing as an aka.
        skip = host == _host and host_path == _path
        if not skip:
            aka_html_path = get_html_path( base, dst_root, _host, _path )
            url = to_urlized( base, urlize, aka_html_path )
            _clear_path = hexlpathutil.to_ascii_path( _path )
            aka.append( '%s: <a href="%s">%s</a><br>' % ( _host, urlfix.fix(url), _clear_path ) )
    metadata.visit( md, aka_fn )
    aka.sort()
    return aka

def to_urlized( base, urlize, path ):
    urlized = re.sub( "^" + base, urlize, path )
    #visit_core.log()
    return urlized

def get_html_path( base, dst_root, host, host_path ):
    hostname = os.path.basename( host_path )
    hostname = re.sub( "\.", "_", hostname )
    hp_base = os.path.basename( host_path )
    if hp_base and hp_base != "":
        hp_base += ".html"
    html_path = os.path.join(
        base,
        get_html_parent_path( base, dst_root, host, host_path ),
        hp_base,
        )
    #visit_core.logVars( locals() )
    return html_path

def get_html_filename( html_path ):
    f = os.path.basename( html_path )
    return f

def get_html_nameorig( html_path ):
    f = get_html_filename( html_path )
    f = f.replace( ".html", "", 1 )
    return f

def get_html_pathorig( html_path ):
    p = html_path.replace( ".html", "", 1 )
    return p

def build_breadcrumbs( base, dst_root, urlize, host, host_path ):
    #visit_core.log()
    bs = []
    preslash = os.path.sep if host_path.startswith( os.path.sep ) else ''
    href_prefix = get_html_path( base, dst_root, host, '' )
    #visit_core.log( "-- %s\n" % href_prefix )
    path_list = hexlpathutil.path_to_list( host_path ) # e.g. /a/b/c -> [a,b,c] where a,b are dirs, c is file.
    #visit_core.log( " -- %s\n" % path_list )
    for i in range( 0, len(path_list)-1 ):
        #visit_core.log( "i=%s path_list=%s bs=%s\n" % ( i, path_list, bs ) )
        cursor = os.path.join( *path_list[0:i+1] )
        a_href = to_urlized( base, urlize, os.path.join( href_prefix, cursor ) )
        a_txt = path_list[i]
        #visit_core.log( "cursor=%s a_href=%s a_txt=%s\n" % ( cursor, a_href, a_txt ) )
        bs.append( '\n<a href="%s">%s</a>' % ( urlfix.fix(a_href), a_txt ) )
        #visit_core.log( "bs = %s\n" % bs )
    #visit_core.log( "bs final = %s\n" % bs )
    bcs = host + ": " + preslash + "/".join( bs ) + "\n"
    #visit_core.log( "%s\n" % bcs )
    return bcs

def get_generated_image_path( base, dst_root, sum_path, modifier ):
    if modifier == None:
        visit_core.log_error( 'missing modifier argument' )
        sys.exit(1)
    #visit_core.log()
    genimg_path = os.path.join(
        base,
        dst_root,
        ".genimgs",
        util.get_data_path_mids( util.get_checksum_from_path( sum_path ) ),
        os.path.basename( sum_path )
        ) + "_" + modifier + ".jpg"
    #visit_core.log( "%s\n" % genimg_path )
    return genimg_path

def get_thumbnail_path( base, dst_root, sum_path ):
    return get_generated_image_path( base, dst_root, sum_path, "thumb" )

def get_raw2png_path( base, dst_root, sum_path ):
    return get_generated_image_path( base, dst_root, sum_path, "wasraw" )

def get_sum2web_path( path ):
    # match: write_thumbnail save "PNG".
    return '%s_%s.%s' % (path, util.WEB_MODIFIER, 'png')

def write_thumbnail( base, urlize, sum_path, html_path, thumb_path ):
    def writer( i, size, out_path ):
        visit_core.log('writer: %s %s\n' % (size, out_path))
        i.thumbnail( (size,size) )
        util.ensure_parent_path( out_path )
        if os.path.exists( out_path ):
            os.remove( out_path )
        # match: get_sum2web_path 'png'.
        i.save( out_path, "PNG" )
    try:
        i = Image.open( sum_path )
        i = i.convert( 'RGB' )
        (iw, ih) = i.size
        s3u_path = get_sum2web_path( sum_path )
        visit_core.logVars( sum_path, html_path, thumb_path )
        visit_core.log( 'write_thumbnail: s3u_path = %s\n' % s3u_path )
        if iw > util.WEB_SIZE or ih > util.WEB_SIZE:
            writer( i, util.WEB_SIZE, s3u_path )
        elif not os.path.exists( s3u_path ):
            os.symlink( sum_path, s3u_path )
        writer( i, THUMBNAIL_SIZE, thumb_path )
        orig_path = get_html_pathorig( html_path )
        sym_path = get_sym_path( orig_path )
        alias_url = to_urlized( base, urlize, sym_path )
        thumb_url = to_urlized( base, urlize, thumb_path )
        visit_core.log( '%s %s\n' % ( alias_url, thumb_url ) )
        return alias_url, thumb_url
    except:
        ex = sys.exc_info()
        if ("cannot identify" in str(ex[1])):
            pass
#        if ("has no attribute '__getitem__'" in str(ex[1])):
#            pass
        else:
            visit_core.log( "sum_path=%s, html_path=%s, ex = %s, %s\n" % (sum_path, html_path, ex, traceback.format_exception(*ex)) )
        return None, None

def build_thumbnail( base, dst_root, urlize, sum_path, html_path ):
    #visit_core.log()
    thumb_path = get_thumbnail_path( base, dst_root, sum_path )
    return write_thumbnail( base, urlize, sum_path, html_path, thumb_path )

def build_name_link( base, urlize, sum_path, html_path ):
    sym_path = get_sym_path( get_html_pathorig(html_path) )
    if not os.path.exists( sym_path ):
        util.ensure_parent_path( sym_path )
        os.symlink( sum_path, sym_path )
    href = to_urlized( base, urlize, sym_path )
    text = re.sub( ".(htm|html)$", "", os.path.basename( sym_path ) )
    l = '<a href="%s">%s</a>' % ( urlfix.fix(href), text )
    #visit_core.logVars( base, urlize, sum_path, html_path, sym_path, l )
    return l

# This was really screwed up somehow, looking at the final outputs!?
def write_by_ext( base, dst_root, sum_path, host, host_path, md, dry_run, over_write ):
    return False
# todo:
#     try:
#         write_by_ext_throws( base, dst_root, sum_path, host, host_path, md, dry_run, over_write )
#     except:
#         visit_core.log_error( "%s\n" % traceback.format_exception(*sys.exc_info()) )
#         visit_core.log_error( "%s\n" % ", ".join( [ host, host_path ] ) )
#
# def write_by_ext_throws( base, dst_root, sum_path, host, host_path, md, dry_run, over_write ):
#     ext = util.get_extension( host_path )
#     if (not dry_run) and (ext in gExts):
#         csum = util.get_checksum_from_path( sum_path )
#         sum_basename = os.path.basename( sum_path )
#         xdir = os.path.join( dst_root, "by_extension", ext, util.get_data_path_mids(csum), sum_basename)
#         util.ensure_path( xdir )
#         ext_path = re.sub( "\.(htm|html)$", "", os.path.join( xdir, os.path.basename(host_path) ) ) + ".html"
#         if os.path.exists( ext_path ) and over_write:
#             os.remove( ext_path )
#         if not os.path.exists( ext_path ):
#             # TODO: it would be better to write a new html file that only lists all akas.
#             html_path = get_html_path( base, dst_root, host, host_path )
#             visit_core.logVars( html_path, ext_path )
#             os.symlink( html_path, ext_path )
#         #visit_core.logVars( base, dst_root, sum_path, host, host_path, md, dry_run, over_write, html_path, ext_path )
#         return True
#     return False

def write_raw2png( sum_path, dst_path, md ):
    smells_like_raw = reduce(
        lambda p, r: r or util.smells_like_raw(p),
        metadata.get_paths( md ),
        False
        )
    if not smells_like_raw:
        #visit_core.log( "not raw" )
        return None
    if os.path.exists( dst_path ): # todo: or forced by flag?
        #visit_core.log( "exists %s" % dst_path )
        return dst_path
    import raw_convert
    # uh, i guess this is defaulting to png?
    raw_convert.raw_convert( sum_path, dst_path )
    return dst_path

def write_image_nonraw( base, dst_root, urlize, sum_path, md ):
    png_path = get_raw2png_path( base, dst_root, sum_path )
    png_path = write_raw2png( sum_path, png_path, md )
    url = None
    if png_path:
        # todo: return url to download image, this is bad. :-(
        url = "file://%s" % png_path
    #visit_core.log()
    png_url = to_urlized( base, urlize, png_path )
    return png_url

def write_image_by_date( base, dst_root, urlize, host, host_path, md, dry_run, over_write, thumb_img_url ):
    #visit_core.log()
    try:
        write_image_by_date_throws( base, dst_root, urlize, host, host_path, md, dry_run, over_write, thumb_img_url )
    except:
        visit_core.log_error( "%s\n" % traceback.format_exception(*sys.exc_info()) )
        visit_core.log_error( "%s\n" % ", ".join( [ host, host_path ] ) )

def write_image_by_date_throws( base, dst_root, urlize, host, host_path, md, dry_run, over_write, thumb_img_url ):
    #visit_core.log()
    oldest_date = metadata.get_oldest( md )
    if (not dry_run) and (oldest_date != None):
        html_path = get_html_path( base, dst_root, host, host_path )
        html_url = to_urlized( base, urlize, html_path )

        # heck only knows if this date stuff is right; i hate python.
        dt = datetime.utcfromtimestamp( oldest_date )
        day_path = os.path.join( base, dst_root, IMAGE_BY_DATE_DIRNAME, str(dt.year), str(dt.month), str(dt.day) )
        util.ensure_path( day_path )
        #visit_core.logVars( html_path, html_url, day_path )

        # write into thumbnail sheet for day.
        # (generally speaking, too many images per month or per year.)
        update_bydatesheet( day_path,
                            ("%s/%s/%s" % (str(dt.year), str(dt.month), str(dt.day))),
                            ("%s:%s" % (host, host_path)),
                            thumb_img_url,
                            html_url,
                            )
        return True
    return False

def update_bydatesheet( day_path, title, orig_name, thumb_img_url, html_url ):
    #visit_core.log()
    if thumb_img_url:
        json_path = os.path.join( day_path, gThumbnailJSONFileName )
        sheet_path = os.path.join( day_path, gThumbnailFileName )
        ensure_bydatepath( title, json_path )
        insert_into_bydatesheet( orig_name, thumb_img_url, html_url, title, json_path, sheet_path )

def ensure_bydatepath( title, json_path ):
    #visit_core.log()
    util.ensure_parent_path( json_path )

def insert_into_bydatesheet( orig_name, thumb_img_url, html_url, title, json_path, sheet_path ):
    #visit_core.log()
    json_data = merge_thumb_json( orig_name, thumb_img_url, html_url, json_path )
    write_thumb_json_bydatesheet( title, json_data, sheet_path )

def merge_thumb_json( orig_name, thumb_img_url, html_url, json_path ):
    # pretty arbitrary which one gets used as the single representative.
    # but shouldn't matter since they should all have akas.
    json_data = {}
    if os.path.isfile( json_path ):
        try:
            jf = open( json_path, "r" )
            json_data = json.load( jf )
            if not type(json_data) is dict:
                sys.stderr.write( "json.load() wasn't a dict: %s\n" % json_path )
                return False
        except Exception, e:
            sys.stderr.write( "failed to json.load(): %s\n" % json_path )
        finally:
            jf.close()
    if not thumb_img_url in json_data:
        json_data[ thumb_img_url ] = {'orig_name':orig_name, 'html_url':html_url, 'thumb_img_url':thumb_img_url}
        try:
            if os.path.exists( json_path ):
                os.remove( json_path )
            f = open( json_path, 'w' )
            f.write( json.dumps(json_data) )
        finally:
            f.close()
    return json_data

def write_thumb_json_bydatesheet( title, json_data, sheet_path ):
    html = render_bydatesheet_html( title, json_data )
    f = open( sheet_path, "w" )
    f.write( html )
    f.close()

def render_bydatesheet_html( title, json_data ):
    #visit_core.log()
    html = g_sheet_htmlt
    html = re.sub( "<!-- title -->", title, html, 1 )
    pre, mid, post = re.split( "<!-- mark -->\n", html )
    l = re.split( "\n", mid )
    for thumb_key in json_data:
        thumb_data = json_data[thumb_key]
        line = '<!-- %s -->'			% thumb_data['orig_name'] +\
            '<a href="%s">'			% urlfix.fix(thumb_data['html_url']) +\
            '<img src="%s" alt="%s"></a>'	% (urlfix.fix(thumb_data['thumb_img_url']), thumb_data['orig_name'])
        l.append( line )
    # misc paranoia.
    l.sort()
    u = util.uniq( l )
    bulky = pre + "<!-- mark -->\n" + "\n".join( u ) + "\n<!-- mark -->\n" + post
    hacked = re.sub( "\n+", "\n", bulky )
    return hacked

def write_html( base, dst_root, urlize, sum_path, host, host_path, md, html_path, dry_run, over_write, thumb_alias_url, thumb_img_url ):
    #visit_core.log()
    try:
        host_path = util.make_safelength_path( host_path )
        write_html_throws( base, dst_root, urlize, sum_path, host, host_path, md, html_path, dry_run, over_write, thumb_alias_url, thumb_img_url )
    except:
        visit_core.log_error( "%s\n" % traceback.format_exception(*sys.exc_info()) )
        visit_core.log_error( "%s\n" % ", ".join( [ sum_path, host, host_path ] ) )

def write_html_throws( base, dst_root, urlize, sum_path, host, host_path, md, html_path, dry_run, over_write, thumb_alias_url, thumb_img_url ):
    #visit_core.log()
    do_write = over_write or (not os.path.exists( html_path ))
    if (not dry_run) and do_write:
        breadcrumbs = build_breadcrumbs( base, dst_root, urlize, host, host_path )
        name_link = build_name_link( base, urlize, sum_path, html_path )
        human_length = util.to_named_size( util.get_length_from_path( sum_path ) )
        sum_url = to_urlized( base, urlize, sum_path )
        is_image = thumb_alias_url and thumb_img_url
        aka = build_aka( base, dst_root, urlize, host, host_path, html_path, md )

        # some day worry about the other mime types as well.
        mime_types = metadata.guess_mime_types( md )
        if mime_types != None:
            mime_type = 'type="%s"' % mime_types[0]
        else:
            mime_type = 'type=unknown'

        if os.path.exists( html_path ):
            os.remove( html_path )
        f = open( html_path, 'w' )
        f.write( '<html><body>\n' )
        f.write( '<table>\n' )
        f.write( '<tr><td bgcolor="#ffcccc" align="right">Path:</td>\n<td>%s/%s</td></tr>\n' % (breadcrumbs, name_link) )
        f.write( '<tr><td bgcolor="#ccffcc" align="right">Name:</td>\n<td>%s</td></tr>\n' % name_link )

        def write_labeled_img(f2, dst_url, thumb_url, text):
            f2.write( '<tr><td colspan="2">' )
            f2.write( '<div class="image" style="background:gray; position:relative; width:100%;">' )
            f2.write( '<a href="%s">' % urlfix.fix(dst_url) )
            f2.write( '<img style="min-width:320px; height:auto;" src="%s" />' % urlfix.fix(thumb_url) )
            f2.write( '<h2 style="color:black; position:absolute; right:0; bottom:0;">%s</h2>' % text )
            f2.write( '</a>' )
            f2.write( '</div>' )
            f2.write( '</tr></td>' )

        if is_image:
            f.write( '<tr><td colspan="2"><hr></td></tr>\n' )
            f.write( '<tr><td colspan="2">Here is a <em>low-resolution</em> thumbnail.</td></tr>\n' )
            f.write( '<tr><td colspan="2">Click on it to see/download the original.</td></tr>\n' )
            ext = util.get_extension( host_path )
            write_labeled_img( f, thumb_alias_url, thumb_img_url, ext )
            nonraw_img_url = write_image_nonraw( base, dst_root, urlize, sum_path, md )
            if nonraw_img_url != None:
                f.write( '<tr><td colspan="2"><hr></td></tr>\n' )
                f.write( '<tr><td colspan="2">NON-RAW .PNG:</td></tr>\n' )
                write_labeled_img( f, nonraw_img_url, thumb_img_url, 'PNG' )
                f.write( '<tr><td colspan="2"><hr></td></tr>\n' )

        f.write( '<tr><td align="right">Original Size:</td>\n<td>%s</td></tr>\n' % human_length )
        f.write( '<tr><td align="right">Canonical:</td>\n<td><a id="canonical" %s href="%s">%s</a></td></tr>\n' % ( mime_type, urlfix.fix(sum_url), os.path.basename(sum_path) ) )

        if aka:
            aka_str = '<tr><td align="right">AKA:</td><td></td></tr>\n' + \
                        '\n'.join( map( lambda a: '<tr><td></td><td>%s</td></tr>\n' % a, aka ) )
            aka_str = aka_str.replace( '<td></td></tr>\n<tr><td></td>', '', 1 )
            f.write( aka_str )

        f.write( '</table>\n' )
        f.write( '\n<body><html>\n' )
        f.close()
        os.chmod( html_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH )
        update_sheet( base, dst_root, urlize, html_path, sum_path, thumb_img_url )
    #visit_core.log( "%s -> %s\n" % ( html_path, sum_path ) )

def update_sheet( base, dst_root, urlize, html_path, sum_path, thumb_img_url ):
    #visit_core.log()
    if thumb_img_url:

        # a (kinda stupid) name to make it show up first in the apache directory listings.
        sheet_path = os.path.join( os.path.dirname( html_path ), "000_thumbnails.html" )

        # "sheet" is less clear i than "thumbnails" i think so rename them.
        old_sheet_path = os.path.join( os.path.dirname( html_path ), "000_sheet.html" )
        if os.path.exists( old_sheet_path ):
            shutil.move( old_sheet_path, sheet_path )

        ensure_sheet( base, dst_root, sheet_path )
        insert_into_sheet( base, urlize, sheet_path, html_path, thumb_img_url )

def ensure_sheet( base, dst_root, sheet_path ):
    #visit_core.log()
    util.ensure_parent_path( sheet_path )
    write_sheet( base, dst_root, sheet_path )

def write_sheet( base, dst_root, sheet_path ):
    #visit_core.log()
    if not os.path.exists( sheet_path ):
        title = os.path.dirname( sheet_path )
        title = title.replace( os.path.join( base, dst_root ), '', 1 )
        html = g_sheet_htmlt
        html = re.sub( "<!-- title -->", title, html, 1 )
        f = open( sheet_path, "w" )
        f.write( html )
        f.close()

def insert_into_sheet( base, urlize, sheet_path, html_path, thumb_img_url ):
    #visit_core.log()
    f = open( sheet_path, "r" )
    html = "".join( f.readlines() )
    f.close()
    html = insert_into_sheet_html( base, urlize, html, html_path, thumb_img_url )
    f = open( sheet_path, "w" )
    f.write( html )
    f.close()

def insert_into_sheet_html( base, urlize, html, html_path, thumb_img_url ):
    #visit_core.log()
    html_url = to_urlized( base, urlize, html_path )
    pre, mid, post = re.split( "<!-- mark -->\n", html )
    l = re.split( "\n", mid )
    orig_name = get_html_nameorig(html_url)
    line = '<!-- %s -->'			% orig_name +\
           '<a href="%s">'			% urlfix.fix(html_url) +\
           '<img src="%s"></a>'			% urlfix.fix(thumb_img_url)
    #visit_core.log( "%s\n" % line )
    l.append( line )
    l.sort()
    u = util.uniq( l )
    bulky = pre + "<!-- mark -->\n" + "\n".join( u ) + "\n<!-- mark -->\n" + post
    hacked = re.sub( "\n+", "\n", bulky )
    return hacked

def s3_upload_path( s3u, path ):
    # fortunately our filenames are already (supposedly) guaranteed unique.
    key = '/'.join(util.extract_parent_path_mids( path )) + '/' + util.get_basename_from_path(path)
    visit_core.log( 'key=%s <- %s\n' % (key, path) )
    try:
        if not s3u.exists( key ):
            s3u.upload( path, key )
    except Exception as e:
        visit_core.log_error( 's3_upload_image: key=%s <- %s %s\n' % (key, path, e) )
        raise e

def s3_upload_image( s3u, sum_path, dry_run ):
    if s3u != None and not dry_run:
        # upload both the hash_len-named-file and the metadata.
        # to save time (bandwidth), prefer only uploading web sized images.
        web_path = get_sum2web_path( sum_path )
        if os.path.exists( web_path ):
            s3_upload_path( s3u, web_path )
        else:
            s3_upload_path( s3u, sum_path )
        md_path = util.data_to_json_metadata_path( sum_path )
        s3_upload_path( s3u, md_path )

def build_html( base, dst_root, urlize, sum_path, md, dry_run, over_write, crawl_spec, s3u=None ):
    #visit_core.log()
    def build_fn( _md, _host, _path, _pathData, _fnData ):
        #visit_core.log()
        host_path = hexlpathutil.to_ascii_path( _path )
        thumb_alias_url, thumb_img_url = (None, None)
        html_path = get_html_path( base, dst_root, _host, host_path )

        if not dry_run:
            ensure_dir_path( base, dst_root, _host, host_path )
            thumb_alias_url, thumb_img_url = build_thumbnail( base, dst_root, urlize, sum_path, html_path )

        is_image = thumb_alias_url and thumb_img_url
        do_write = (crawl_spec == gCrawlEverything) or (crawl_spec == gCrawlImagesOnly and is_image) or (crawl_spec == gCrawlNotImages and not is_image) or False
        visit_core.logVars( _path, html_path, crawl_spec, thumb_alias_url, thumb_img_url, do_write )
        visit_core.log('i?%s w?%s %s\n' % (is_image, do_write, util.get_basename_from_path(sum_path)))
        if do_write:
            write_html( base, dst_root, urlize, sum_path, _host, host_path, _md, html_path, dry_run, over_write, thumb_alias_url, thumb_img_url )
            write_by_ext( base, dst_root, sum_path, _host, host_path, _md, dry_run, over_write )
            if is_image:
                visit_core.log('image: %s\n' % util.get_basename_from_path(sum_path))
                write_image_by_date( base, dst_root, urlize, _host, host_path, _md, dry_run, over_write, thumb_img_url )
                s3_upload_image( s3u, sum_path, dry_run )
    metadata.visit( md, build_fn )

# ----------------------------------------

def test_get_html_parent_path():
    p = get_html_parent_path( "base", "dst_root", "host", "path1/path2/file" )
    assert p == "base/dst_root/host/path1/path2", p

def test_ensure_dir_path():
    if os.path.exists( "/tmp/foobar" ):
        shutil.rmtree( "/tmp/foobar" )
    ensure_dir_path( "/tmp/foobar", "dst", "test.example.com", "1/2/3/origname" )
    assert os.path.exists( "/tmp/foobar/dst/test.example.com/1/2/3/" )

def test_ensure_dir_path_hostsafe():
    if os.path.exists( "/tmp/foobar" ):
        shutil.rmtree( "/tmp/foobar" )
    ensure_dir_path( "/tmp/foobar", "dst", "test/example/com", "1/2/3/origname" )
    assert os.path.exists( "/tmp/foobar/dst/test_example_com/1/2/3/" )

def test_build_html_createsdirs():
    import binascii
    root = "/var/www/html/jces"
    subdir = "tmp/foobar"
    basepath = "%s/%s"%(root,subdir)
    if os.path.exists( basepath ):
        shutil.rmtree( basepath )
    srcpath = "%s/src"%basepath
    dstpath = "%s/dst"%basepath
    os.makedirs( srcpath )
    # has to be a sum_name, can't be a regular name.
    fname = "173f85b0a7cd9c067089756e597a7fa8_9698127"
    shutil.copyfile( "itest_nef/%s"%fname, "%s/%s"%(srcpath,fname))
    # todo: another nef file or something, to see if thumbnail sheets work better now.
    timestamp_sec = 1497136500 
    day = 24*60*60
    md = { metadata.VERSION_KEY: metadata.LATEST_VERSION,
           metadata.HOSTS_KEY:
               { 'host.1.com':
                     { metadata.PY_PLATFORM_SYSTEM_KEY: 'Linux',
                       metadata.PY_PLATFORM_UNAME_KEY: ('system', 'node', 'release', 'version', 'machine', 'processor'),
                       metadata.PY_BYTEORDER_KEY: 'little',
                       metadata.PATHS_KEY:
                           { binascii.hexlify('1/2/3/A.nef'):
                                 { metadata.LAST_UPDATE_SEC_KEY: timestamp_sec,
                                   metadata.OLDEST_TIMESTAMP_KEY: timestamp_sec,
                                   metadata.EXE_KEY: False,
                                   metadata.PY_FILEPATH_ENCODING_KEY: 'UTF-8',
                                   metadata.PY_PATH_SEP_KEY:os.path.sep
                                   }
                             }
                       }
                 }
           }
    build_html( basepath,
                "dst",
                "http://monad.com/jces/%s"%subdir,
                "%s/%s"%(srcpath,fname),
                md,
                False,
                True,
                gCrawlEverything )
    assert os.path.exists( "%s/host.1.com/1/2/3/"%(dstpath) )
    #assert os.path.exists( "%s/host.2.com/1/2/3/"%(dstpath) )

def test_get_sym_path():
    s = get_sym_path( "/var/www/html/jces/tmp/pybak/openvz.monad.com/vz/storage/Ian/UploadedIThink/SleepingJuly2010/IMG_2010.JPG" )
    expected = "/var/www/html/jces/tmp/pybak/openvz.monad.com/vz/storage/Ian/UploadedIThink/SleepingJuly2010/.syms/IMG_2010.JPG"
    assert s == expected, s

def test():
    test_get_sym_path()
    test_get_html_parent_path()
    test_ensure_dir_path()
    test_ensure_dir_path_hostsafe()
    test_build_html_createsdirs()

def usage(msg=None):
    if msg:
        visit_core.log_error("%s\n" % msg)
    visit_core.log_error( "usage: %s {--dryrun} {--overwrite} {--maxdepth N} {--images-only/--not-images} <root> <root_url> <(root)/canonical> <(root)/browse>\n" % sys.argv[0] )
    sys.exit(1)
    
if __name__ == '__main__':
    if util.eat_arg( sys.argv, "test" ):
        test()
    else:
        try:
            dm = visit_core.main_helper( usage )
            dry_run = dm['dry_run']
            max_depth = dm['max_depth']
            # todo: seems like these should be supported via main_helper instead.
            over_write = util.eat_arg( sys.argv, "overwrite", remove=True )
            images_only = util.eat_arg( sys.argv, "images-only", remove=True )
            not_images = util.eat_arg( sys.argv, "not-images", remove=True )
            if( images_only and not_images ):
                raise Exception( "--images-only & --not-images flags are mutually exclusive." )
            crawl_spec = gCrawlEverything
            if( images_only ):
                crawl_spec = gCrawlImagesOnly
            elif( not_images ):
                crawl_spec = gCrawlNotImages
            g_font = font.get_font()
            root = os.path.abspath( sys.argv[1] )
            urlize = sys.argv[2]
            canonical = sys.argv[3]
            browse = sys.argv[4]
            canonical_root = os.path.join( root, canonical )
            browse_root = os.path.join( root, browse )
        except Exception as e:
            usage(msg="args: %s\nERROR: %s" % (traceback.format_exception(*sys.exc_info()), e))

        def visit_single( file_count, full_path, data ):
            visit_core.log( "%s %s\n" % ( file_count, full_path ) )
            try:
                if os.path.isfile( full_path ) and util.smells_like_canonical( full_path ):
                    md = metadata.read_json_path( util.data_to_json_metadata_path( full_path ) )
                    build_html( root, browse_root, urlize, full_path, md, dry_run, over_write, crawl_spec, data['s3u'] )
            except Exception as e:
                visit_core.log_error( "%s\n" % str(e) )

        try:
            data = { 's3u': S3Upload(get_bucket_name()) }
            visit_core.visit( canonical_root, max_depth, visit_single, None, data )
        except:
            usage(msg="run: %s" % traceback.format_exception(*sys.exc_info()))
