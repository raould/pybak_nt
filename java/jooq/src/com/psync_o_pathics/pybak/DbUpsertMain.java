package com.psync_o_pathics.pybak;

import java.nio.file.*;
import java.nio.file.attribute.*;
import java.io.*;
import java.util.*;
import org.jooq.*;

public class DbUpsertMain {
    public static void main( String[] args ) {
        CrawlFramework crawler = new CrawlFramework( args, new PybakVisitor() );
        crawler.crawl();
    }
}
