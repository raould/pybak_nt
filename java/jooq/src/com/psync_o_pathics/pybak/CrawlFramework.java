package com.psync_o_pathics.pybak;

import java.nio.file.*;
import java.nio.file.attribute.*;
import java.io.*;
import java.util.*;
import org.jooq.*;

public class CrawlFramework<T> {

    public static abstract class CrawlVisitor extends SimpleFileVisitor<Path> {
        private DSLContext dslContext;
        public void setDSLContext( DSLContext dslContext ) {
            this.dslContext = dslContext;
        }
        public DSLContext getDSLContext() {
            return dslContext;
        }
    }

    final Path canonicalRoot;
    final String userName;
    final String password;
    final String url;
    final String driverName;
    final CrawlVisitor visitor;

    public CrawlFramework( String[] args, CrawlVisitor visitor ) {
        if( args.length != 5 ) {
            throw new RuntimeException( "args: <canonical_dir> <user_name> <password> <url> <driver_name>" );
        }
        this.canonicalRoot = Paths.get( args[0] );
        this.userName = args[1];
        this.password = args[2];
        this.url = args[3];
        this.driverName = args[4];
        this.visitor = visitor;
    }

    public void crawl() {
        try {
            DSLContext dslContext = Connection.s_getDSLContext( userName, password, url, driverName );
            visitor.setDSLContext( dslContext );
            Files.walkFileTree( canonicalRoot, visitor );
        }
        catch( Exception exc ) {
            System.err.println( exc );
        }
    }
}
