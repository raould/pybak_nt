package statHash;

my( $kSomething ) = 'found';
my( $kBlank ) = 'blank';
my( $kStore ) = 'store';

my( %statHash );

sub get
{
    my( $key ) = shift;
    
    my( $count );
    if( !defined( $statHash{$key} ) )
    {
	$count = 0;
    }
    else
    {
	$count = $statHash{$key};
    }

    return( $count );
}

sub increment
{
    my( $key ) = shift;

    if( ! defined( $statHash{$key} ) )
    {
	$statHash{ $key } = 1;
    }
    else
    {
	$statHash{ $key }++;
    }
}

sub recordStore
{
    increment( $kStore );
}

sub recordGotSomething
{
    increment( $kSomething );
}

sub recordGotBlank
{
    increment( $kBlank );
}

sub getStats
{
    my( $string );

    $string = "stores: " . get( $kStore ) . "\n";
    $string .= "lookup, failure: " . get( $kBlank ) . "\n";
    $string .= "lookup, success: " . get( $kSomething ) . "\n";

    return( $string );
}

1;
