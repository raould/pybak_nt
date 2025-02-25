#!/usr/local/bin/perl -w

package ebayhist;

use strict;
use LWP;
use LWP::UserAgent;
use HTTP::Request;
use HTTP::Response;

#http://search-completed.ebay.com/search/search.dll?ht=1&query=foo+bar&SortProperty=MetaEndSort
sub FetchPriceInfoURL
{
    my( $terms ) = join( ' ', @_ );

    my( $url ) = 'http://search-completed.ebay.com/search/search.dll?ht=1&query=';
    $url .= $terms;
    $url .= '&SortProperty=MetaEndSort';

    return( $url );
}

sub FetchPriceInfo
{
    my( $url ) = FetchPriceInfoURL( @_ );
    my( $ua ) = new LWP::UserAgent();
    my( $content ) = getURLContent( $ua, $url );

#if( open( FHOUT, ">/tmp/ebayhist.html" ) )
#{
#    print FHOUT $content;
#    print FHOUT "\r\n";
#    close( FHOUT );
#}

    my( @prices );
    my( @parts ) = split( /\$/, $content );
    my( $part );
    foreach $part ( @parts )
    {
	# this fails for non-us currencies, where the ',' and '.' are swapped.
	if( $part =~ m/^(\d+[,.\d]*)/ )
	{
	    my( $price ) = $1;
	    $price =~ s/,//g;
	    push( @prices, $price );
	    #print( "found $price\n in $part\n" );
	}
    }

    if( scalar(@prices) == 0 )
    {
	return( 0, 0, 0, 0 );
    }
    else
    {
	my( $maxPrice ) = 0;
	my( $minPrice ) = 999999.99;
	my( $totalPrice ) = 0;
	map
	{
	    if($maxPrice < $_) { $maxPrice = $_; }
	    if($minPrice > $_) { $minPrice = $_; }
	    $totalPrice += $_;
	} @prices;

	my( @ret );
	push( @ret, scalar(@prices) );
	push( @ret, $minPrice );
	push( @ret, $maxPrice );
	push( @ret, $totalPrice );
	return( @ret );
    }
}

sub getURLContent
{
    my( $ua ) = shift;
    my( $url ) = shift;

    my( $req ) = new HTTP::Request( GET => $url );

    # Pass request to the user agent and get a response back
    my( $res ) = $ua->request( $req );

    # Check the outcome of the response
    if( ! $res->is_success )
    {
	print $res->error_as_HTML();
    }

    return( $res->content );
}

1;
