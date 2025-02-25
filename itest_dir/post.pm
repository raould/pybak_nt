#!/usr/local/bin/perl -w
package post;

sub get
{
    my(@parts);

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

	@parts = split( /&/, $in );
    }
    else
    {
	@parts = ();
    }

    print( "\n<!-- parts = ", @parts, " -->\n" );

    return( @parts );
}

1;
