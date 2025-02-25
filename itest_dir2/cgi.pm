#!/usr/local/bin/perl -w

package cgi;

# retun hashref( wordName => wordValue ) from GET method.
sub get
{
    my( $str ) = $ENV{ "QUERY_STRING" };
    #print( "<!-- QUERY_STRING = $str -->\n" );
    return( parseStr( $str ) );
}

# return hashref( wordName => wordValue ) from POST method.
sub read
{
    my(%ret);
    my($in);

    if( $ENV{'REQUEST_METHOD'} eq 'POST' )
    {    
	# Read in text
	read(STDIN,$in,$ENV{'CONTENT_LENGTH'});

	# the CERN proxy server puts null characters in the begining of forms.
	if (ord($in) == 0)
	{
	    print STDERR "CGIPARSE: null in data ";
	    read(STDIN,$intmp,1);
	    $in .= $intmp;
	    $in = substr($in,1);
	}
    }

    print( "<!-- cgi::read $in -->\n" );

    return( parseStr( $in ) );
}

sub parseStr
{
    my( $in ) = shift;

    my(@parts) = split( /&/, $in );

    my( $wordPair );
    foreach $wordPair( @parts )
    {
	my(@wordData) = split( /=/, $wordPair );
	my($wordName) = $wordData[0];
	my($wordVal) = $wordData[1];

	print( "<!-- cgi data: $wordName = $wordVal -->\n" );

	$wordVal =~ s/\+/ /g;
	$wordVal =~ s@\x00@@g;
	while( $wordVal =~ m/\%([a-z0-9][a-z0-9])/i )
	{
	    $hex = $1;
	    $val = pack( "H*", $hex );
	    $wordVal =~ s/\%$hex/$val/g;
	}

	$ret{ $wordName } = $wordVal;
	print( "<!-- cgi data: $wordName = $wordVal -->\n" );
    }

    return( \%ret );
}

1;
