#!/usr/local/bin/perl5 -w

package util;

my( $padStr ) = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";

sub htmlError
{
    my( $str ) = shift;
    print( "<center>\n" );
    print( "<h2>Error</h2>\n" );
    print( "<p>$str\n" );
    print( "<p>(Contact the site administrator.)\n" );
    print( "</center>\n" );
    exit();
}

sub toSafeValue
{
    my( $val ) = shift;
    my( $def ) = shift;

    if( !defined( $val ) )
    {
	$val = $def;
    }

    return( $val );
}

# sort by (beds, desc)(price, asc)
sub toSortKey
{
    my( $a ) = shift;

    my( $aKey ) = "";

    # i think i want the key to be
    # <beds><price-right-justified>

    my($bed) = toSafeValue( $a->{"Bedroom"}, "0" );
    $bed =~ s/\D//g;
    $bed = 10000 - $bed;
    my($bedLen) = length($bed);

    my($pr) = toSafeValue( $a->{ "Price" }, "0" );
    $pr =~ s/\D//g;
    $pr = 999999999999999 - $pr;
    my($prLen) = length($pr);

    my($padding) = substr( $padStr, 0, 40 - $bedLen - $prLen );

    $aKey .= $bed;
    $aKey .= $padding;
    $aKey .= $pr;

    return( $aKey );
}

sub formatDate
{
    my($value) = shift;

    #print( "<!-- foo = ", length($value), " -->\n" );

    if( defined($value) && length( $value ) == 8 &&
       ( ($value =~ m/^19.*/) || ($value =~ m/^20.*/) ) )
    {
	my( $date );
	$date = substr( $value, 4, 2 );
	$date .= "/";
	$date .= substr( $value, 6, 2 );
	$date .= "/";
	$date .= substr( $value, 2, 2 );
	$value = $date;
    }

    return( $value );
}

sub comma
{
    my( $value ) = shift;

    $value = reverse( $value );
    my(@ray) = split( //, $value );
    my(@new);
    my($dex);
    for $dex ( 0 .. scalar(@ray)-1 )
    {
	push( @new, $ray[$dex] );
	if( $dex % 3 == 2 && $dex != 0 && $dex != scalar(@ray)-1 ) { push( @new, "," ); }
    }
    $value = join( "", @new );
    $value = reverse( $value );

    return( $value );
}

# keith determined this should be the right fn.
sub pmt
{
    my( $i, $n, $l ) = @_;

    my( $rez );

    $rez = ( $i/12 * ((1+$i/12)**(12*$n)) * $l ) / ( ((1+$i/12)**(12*$n)) - 1 );    

    return( $rez );
}

# hash => hidden name, value pairs in a big string.
sub toHiddenStr
{
    my( $hashRef ) = shift;

    my( $str ) = "";

    my( $key, $value );
    foreach $key ( keys( %{$hashRef} ) )
    {
	$value = $hashRef->{ $key };
	$value =~ s/\"//g;
	$str .= "<input type=\"hidden\" name=\"$key\" value=\"$value\"\>\n";
    }

    return( $str );
}

sub orderWord
{
    my( $word ) = shift;

    my( @letters ) = explode( $word );
    @letters = sort( @letters );
    my( $sorted ) = join( '', @letters );
    return( $sorted );
}

sub explode
{
    my( $word ) = shift;

    my( @ray );
    my( $idx );

    for( $idx = 0; $idx < length($word); $idx++ )
    {
	push( @ray, substr( $word, $idx, 1 ) );
    }

    return( @ray );
}

1;
