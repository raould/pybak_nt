package com.psync_o_pathics.pybak;

import java.sql.*;
import org.jooq.*;
import org.jooq.impl.*;
import static org.jooq.impl.DSL.*;
import com.psync_o_pathics.db.tables.Tables;

public class Connection {
    public static DSLContext s_getDSLContext( String userName, String password, String url, String driverName ) 
    throws Exception {
        Class.forName( driverName ).newInstance();
        java.sql.Connection conn = java.sql.DriverManager.getConnection( url, userName, password );
        DSLContext context = DSL.using( conn, SQLDialect.POSTGRES );
        return context;
    }
}
