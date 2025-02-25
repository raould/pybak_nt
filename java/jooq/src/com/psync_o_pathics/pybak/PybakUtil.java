package com.psync_o_pathics.pybak;

import com.psync_o_pathics.pybak.util.*;
import java.nio.file.*;
import java.util.*;
import java.io.*;
import static org.apache.commons.lang3.ArrayUtils.*;

public class PybakUtil {

    public static final Pair<String,String> getSumAndLengthFromMetadataPath( Path path ) {
	String dataPath = path.toString().replace( Metadata.JSON_DOTEXT, "" );
	return getSumAndLengthFromPath( Paths.get( dataPath ) );
    }

    public static final Pair<String,String> getSumAndLengthFromPath( Path path ) {
	assert Files.exists( path );
	String filename = path.getFileName().toString();
	String[] parts = filename.split( "_" );
	assert parts.length == 2;
	return new Pair<String,String>( parts[0], parts[1] );
    }

    public static final boolean isMetadataJson( Path path ) {
        boolean isRegularFile = Files.isRegularFile( path, LinkOption.NOFOLLOW_LINKS );
        boolean nameMatches = path.toString().toLowerCase().endsWith( ".mdj" );
        return isRegularFile && nameMatches;
    }

    /**
     * assumes utf-8.
     */
    public static final List<Byte> unhexlifyToList( String hex ) {
        if( hex.length() % 2 != 0 ) {
            throw new RuntimeException( "unhexlify argument must be of even length" );
        }
        List<Byte> bytes = new ArrayList<Byte>();
        for( int i = 0; i < hex.length(); i+=2 ) {
            char c1 = hex.charAt( i );
            char c2 = hex.charAt( i+1 );
            byte b = (byte)((Character.digit(c1, 16) << 4) + Character.digit(c2, 16));
	    bytes.add( b );
        }
	return bytes;
    }

    public static final byte[] unhexlifyToArray( String hex ) {
	List<Byte> bytes = unhexlifyToList( hex );
        return toPrimitive( bytes.toArray(new Byte[bytes.size()]) );
    }

}
