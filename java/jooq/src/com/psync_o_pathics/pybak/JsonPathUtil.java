package com.psync_o_pathics.pybak;

class JsonPathUtil {

  public static String buildPath( String... parts ) {
	final StringBuilder b = new StringBuilder();
	b.append( "$" );
	for( String p : parts ) {
	  b.append( "['" );
	  b.append( p );
	  b.append( "']" );
	}
	return b.toString();
  }

}
