package com.psync_o_pathics.pybak;

import static com.psync_o_pathics.db.tables.Tables.*;
import com.psync_o_pathics.pybak.util.*;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.io.*;
import java.util.*;
import org.jooq.*;

public class PybakVisitor extends CrawlFramework.CrawlVisitor {

    public FileVisitResult visitFile( Path path, BasicFileAttributes attrs ) throws IOException {
        if( PybakUtil.isMetadataJson( path ) ) {
            System.out.println( "reading " + path );
            Metadata md = Metadata.fromPath( path );
            Pair<String,String> sumAndLength = PybakUtil.getSumAndLengthFromMetadataPath( path );
            updateDatabase( getDSLContext(), md, sumAndLength.a, sumAndLength.b );
        }
        return FileVisitResult.CONTINUE;
    }

    private static boolean shouldSkip( Metadata md ) {
	return false;
    }

    private static void updateDatabase( DSLContext dslContext, Metadata md, String sum, String length ) {
	// todo:
	// if the metadata says the file was in a 'pybak/canonical' path
	// (or what others? maybe just 'canonical' anywhere?)
	// then skip it to avoid crawling the old html files.
	if( ! shouldSkip( md ) ) {
	    // todo:
	    // 1) for each host in md
	    // 2) for each path in md[host]
	    // 3) upsert all tables
	    System.out.println( md );
	    upsertCanonical( dslContext, md, sum, length );
	    upsertHosts( dslContext, md );
	    //upsertPaths( dslContext, md );
	}
	System.exit(0);
    }

    private static void upsertCanonical( DSLContext dslContext, Metadata md, String sum, String length ) {
        int count =
            dslContext.
            selectCount().
            from(CANONICAL).
            where(CANONICAL.SUM.equal(sum)).
            and(CANONICAL.LEN.equal(length)).
            fetchOne( 0, Integer.class );
				System.out.println( "upsertCanonical("+sum+","+length+"): count=" + count );
        if( count == 0 ) {
            dslContext.
                insertInto(CANONICAL).
                set(CANONICAL.SUM, sum).
                set(CANONICAL.LEN, length).
                execute();
        }
    }

    private static void upsertHosts( DSLContext dslContext, Metadata md ) {
        for( String host : md.getHostNames() ) {
            int count =
                dslContext.
                selectCount().
                from(HOST).
                where(HOST.HOST_.equal(host)).
                fetchOne( 0, Integer.class );
						System.out.println( "upsertHosts(): host=" + host + ", count=" + count );
            if( count == 0 ) {
                dslContext.
                    insertInto(HOST).
                    set(HOST.HOST_, host).
                    execute();
            }
        }
    }
}
