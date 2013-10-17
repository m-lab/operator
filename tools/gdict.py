#!/usr/bin/env python

import ConfigParser
from datetime import datetime,timedelta
import gdata.spreadsheet.text_db as spreadsheet_textdb
import logging as log
import os
import subprocess
import sys
import time

log.basicConfig(level=log.ERROR, format='%(levelname)-5s: %(message)s')

# TODO: figure out how to get the number of rows in a spreadsheet
#       seems unsupported without fetching everything and counting
MAX_ROW_COUNT=10000

def usage():
    return """
  Summary:

    gdict.py is a scriptable, key-values store that permits queries and
    updates using Google Drive Spreadsheets as a storage backend.

    gdict.py is designed for scripting and as an automation aid. By using
    Google Spreadsheets, the key-values data can be easily viewed, updated by
    hand, or shared.

    gdict.py can be used as both a source of input to scripts and a destination
    for output from scripts.

    gdict.py supports create, show, and update.

  Configuration:
    All parameters can be set on the command line. Common values can be set
    with "spreadsheet.conf", using INI format supported by Python ConfigParser.
    
    gdict.py supports one config section "[main]" and these parameters:
      [main]
      email=        -- email address of google account to access Drive
      password=     -- password of google account
      sheetname=    -- spreadsheet name, visible in Drive
      table=        -- table name (i.e, 'sheet' name in user interface)

  Values From Scripts:

    A nice feature of gdict.py is that it can run subcommands.  The
    subcommands can be passed parameters from values stored in the
    spreadsheet, and values in the spreadsheet can be updated from values
    printed by the script.

    A script is specified using: 
        --results "command [args ...]"

    The command string is treated as a python, format string. So, the current
    values of columns are substituted at run time.  To run 'command' with the
    value in column c1 as the first argument:
        --results "command {c1}"

    The following characters are reserved: '_', '{', '}'
       '_' is interpreted by the gdata module when used in column names.
           However, underscore can be anywhere else.
       '{' and '}' are used in string formatting. They are replaced and the
           --result "command format" should not include extra braces.

    To indicate success, the script should have an exit value of zero. To have
    new values added to the current key, the script should print column,value
    pairs separated by newline to stdout.
        c1,v1\\n
        c2,v2\\n
        c3,v3\\n
    
    All of these values will be associated with the --key given on the command
    line. Every existing column name will be updated with the corresponding
    value.  Non-existent columns will be ignored.  Values for recurring column
    names are concatenated with a space into a single value. There are three
    pre-defined values for:
       {ts} -- the current timestamp as an integer
       {date} -- the current date in the form YYYY-MM-DD
       {date_ts} -- the current date with time in the form YYYY-MM-DDTHH:MM

    To indicate error, the script should have a non-zero exit value. Any
    message to stderr is reported to the user, and any output to stdout is
    ignored.

  Examples:
    Assuming spreadsheet.conf contains values for email, password, and
    spreadsheet:

    # create table, with column names, first column is the keyname
    ./gdict.py --table test --create --columns keyname,c1,c2,c3,c4

    # add values
    ./gdict.py --table test --update --key A --values 2,3,4,5
    ./gdict.py --table test --update --key B --values 0,7,5,3
    ./gdict.py --table test --update --key C --columns c2,c3 --values 9,1

    # add values by script 
    ./gdict.py --table test --update --key D \\
                  --results "echo 'c1,{ts}\\nc2,{c1}\\nc3,{c2}\\nc4,{c3}\\n'"

    # update column c1 to ts where --select matches
    ./gdict.py --table test --update --select 'c1<10' \\
                  --results "echo c1,{ts}"

    # show a single record (with implied query for, keyname=='A')
    ./gdict.py --table test --show --key A

    # show all values in column 'keyname'
    ./gdict.py --table test --show --columns keyname

    # show rows that match '--select' query
    ./gdict.py --table test --show --select 'c2>4'

    # show everything
    ./gdict.py --table test --show """

def read_local_config(options, filename):
    """ Read the given configuration filename and save values in 'options'
        This function recognizes only one section:
            '[main]'
        Within this section, this function recognizes only:
            'sheetname' - name of spreadsheet file in Drive
            'table' - table name within spreadsheet.
            'email' - google account email
            'password' - password for account

        Args:
            options - the options object returned by OptionParser.parse_args()
            filename - filename of config file
        Returns:
            None
    """
    config = ConfigParser.SafeConfigParser()
    if not os.path.exists(filename):
        # NOTE: all options can be passed via command line
        return

    config.read(filename)
    for opt_name in ['email', 'password', 'sheetname', 'table']:
        if not config.has_option('main', opt_name):
            continue
        setattr(options, opt_name, config.get('main', opt_name))
    return

def get_db(client, name, create):
    """ Searches for database 'name'. If the database is not found
    create it if 'create' is True, otherwise exit.
    Args:
        client - DatabaseClient()
        name - string, name of database
        create - bool, whether or not to create if db not found
    Returns:
        gdata.spreadsheet.text_db.Database()
    Exits:
        if database 'name' not found and 'create' is False
    """
    db_list = client.GetDatabases(name=name)
    if len(db_list) == 0:
        if not create:
            log.error("Could not find db %s" % name)
            log.error("Use --create to create it")
            sys.exit(1)
        db = client.CreateDatabase(name)
    else:
        db = db_list[0]
    return db

def get_table(db, table_name, column_names, create):
    """ Searches for table 'table_name'.  If the table is not found
    and 'create' is True, then create the table.  Otherwise, exit.
    Args:
        db - Database(), returned by get_db() or similar
        table_name - string, name of table or 'sheet' in web-UI
        column_names - list of string, column header names
        create - bool, whether or not to create if table not found
    Returns:
        gdata.spreadsheet.text_db.Table()
    Exits:
        if table 'name' not found and 'create' is False
    """
    table_list = db.GetTables(name=table_name)
    if len(table_list) == 0:
        if not create:
            log.error("Could not find table %s" % table_name)
            log.error("Use --create to create it")
            sys.exit(1)

        # NOTE: cannot create a table without headers.
        assert(column_names is not None and len(column_names) > 0 )
        log.info("Creating table: %s" % table_name)
        log.info("With headers: %s" % column_names)
        table = db.CreateTable(table_name, column_names)
    else:
        table = table_list[0]
    return table

def add_record(table, data):
    row = table.AddRecord(data)
    return row

def update_record(record, data):
    record.content.update(data)
    record.Push()
    return record

def get_records(table, config):
    rs=[]
    if config.select:
        rs=table.FindRecords(config.select)
    elif config.key:
        rs=table.FindRecords(config.headers[0]+"=="+config.key)
    else:
        # TODO: need a way to determine total length.
        # NOTE: get everything
        rs = table.GetRecords(1,MAX_ROW_COUNT)
    return rs

def delete_record(rec):
    # TODO: add ability to delete 'rec'
    pass

def parse_args():
    from optparse import OptionParser
    parser = OptionParser(usage=usage())

    # NOTE: spreadsheet configuration & access
    parser.add_option("", "--sheetname", dest="sheetname",
                      default=None,
                      help="Name of Spreadsheet (visible in Google Drive)")
    parser.add_option("", "--table",     dest="table",
                      default=None,
                      help="Table name (i.e. page, sheet) within spreadsheet.")
    parser.add_option("", "--email",     dest="email",
                      default=None,
                      help="user email address")
    parser.add_option("", "--password",  dest="password",
                      default=None,
                      help="application or user password")
    parser.add_option("", "--config",    dest="configfile",
                      default="spreadsheet.conf",
                      help="Config file containing spreadsheet values")

    # OPTIONAL
    parser.add_option("", "--verbose", dest="verbose",
                      default=False, action="store_true",
                      help="Print some extra messages.")

    # NOTE: mutually exclusive options.
    parser.add_option("", "--create", dest="create",
                      default=False, action="store_true",
                      help="Creates a new spreadsheet in GoogleDrive.")
    parser.add_option("", "--update", dest="update",
                      default=False, action="store_true",
                      help="add or update records that match selected rows")
    parser.add_option("", "--show", dest="show",
                      default=False, action="store_true",
                      help="display records that match selected rows")
    parser.add_option("", "--header", dest="header", action="store_true",
                      default=False,
                      help="For --show, print header as first line")
    parser.add_option("", "--delete", dest="delete",
                      default=False, action="store_true",
                      help="TODO: delete records that match selected rows")

    # NOTE: how to specifiy rows, data, or commands that produce data
    parser.add_option("", "--key", dest="key",
                      default=None,
                      help="Row identifier to operate on.")
    parser.add_option("", "--select", dest="select",
                      default=None,
                      help="Select statement to choose rows to operate on.")
    parser.add_option("", "--columns", dest="columns",
                      default=None,
                      help="Column names to operate on.")
    parser.add_option("", "--values", dest="values",
                      default=None,
                      help="Values to associate with corresponding 'column'")
    parser.add_option("", "--results",  dest="results",
                      default=None,
                      help="Excecute the steps for completing a node update.")

    (config, args) = parser.parse_args()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    # NOTE: confirm some options are mutually exclusive
    count = sum([config.create,config.update,config.show,config.delete])
    if count == 0 or count > 1:
        log.error("Specify one of create, update, show, or delete")
        sys.exit(1)

    # NOTE: continue checking arguments
    if config.create:
        if config.columns is None:
            log.error("For --create also specify --columns")
            sys.exit(1)
    if config.update:
        # NOTE: One or the other; not both and not neither.
        if (config.key is None) == (config.select is None):
            log.error("With --update, please specify one of")
            log.error("--key or --select")
            sys.exit(1)

        # NOTE: One or the other; not both and not neither.
        if (config.results is None) == (config.values is None):
            log.error("Specify only one of --results or --values")
            sys.exit(1)

    if config.delete:
        log.error("Sorry, --delete not yet supported")
        sys.exit(1)
        if ((config.key is None and config.select is None) or
            (config.key and config.select)):
            log.error("for --delete specify either --key or --select")
            sys.exit(1)

    # NOTE: Get any local config information
    read_local_config(config, config.configfile)

    if config.email is None or config.password is None:
        log.error("Please provide username & password")
        sys.exit(1)
    if config.sheetname is None or config.table is None:
        log.error("Please provide sheetname & table names")
        sys.exit(1)

    if config.columns:
        config.columns = config.columns.split(',')
    if config.values:
        # NOTE: values are only used during update.
        config.values = config.values.split(',')
        # TODO: maybe add a 'tr' like feature to convert chars after split
        #       in case we want ',' in values
    
    if config.verbose:
        # NOTE: default level is only error() messages.
        # NOTE: enable info() messages as well.
        log.basicConfig(level=log.INFO, format='%(levelname)-5s: %(message)s')

    return (config, args)

def handle_show(table, config):
    if config.columns:
        fields = config.columns
    else:
        fields = config.headers

    if config.header:
        # TODO: maybe support a separator character here.
        print " ".join(fields)

    rs=get_records(table, config)
    for record in rs:
        for key in fields:
            if record.content.has_key(key):
                print record.content[key],
            else:
                log.error("Record does not contain key: '%s'" % key)
                sys.exit(1)
        print ""

def handle_update(table, config):
    rs = get_records(table, config)
    if len(rs) == 0 and config.select:
        log.error("No records returned from --select %s" % config.select)
        log.error("Cannot add new records using --select")
        sys.exit(1)

    if config.values:
        handle_update_values(table, config, rs)
    elif config.results:
        handle_update_results(table, config, rs)
    else:
        log.error("specify --results, or")
        log.error("specify --values")
        sys.exit(1)

def handle_update_values(table, config, rs):
    data_list = []
    if not config.columns and len(config.headers[1:]) == len(config.values):
        new_data = dict(zip(config.headers[1:], config.values))

    elif not config.columns:
        val_len = len(config.values) # don't include first, keyname col
        col_len = len(config.headers[1:]) # don't include first, keyname col
        log.error("Number of --values given does not match the number of")
        log.error("columns available: %s vs %s" % (val_len, col_len))
        log.error("Either, specify --values with --columns, or ")
        log.error("specify %s values for all columns." % col_len)
        sys.exit(1)

    elif config.columns and len(config.columns) == len(config.values):
        # NOTE: this could be used to update the 'key', maybe not ideal.
        new_data = dict(zip(config.columns, config.values))

    elif config.columns:
        val_len = len(config.values) # don't include first, keyname col
        col_len = len(config.columns) # don't include first, keyname col
        log.error("Number of --values given does not match")
        log.error("Number of --columns given: %s vs %s" % (val_len, col_len))
        sys.exit(1)

    new_data.update({config.headers[0] : config.key})

    if len(rs) == 0:
        # NOTE: there was no field found, so add it.
        log.info("Adding data: %s" % new_data)
        add_record(table, new_data)
        return
 
    # NOTE: len(rs) > 0
    for rec in rs:
        log.info("Updating data to", new_data)
        update_record(rec, new_data)
    return

def handle_update_results(table, config, rs):
    if len(rs) == 0:
        # NOTE: treat the first column as the key for row.
        default_data = {config.headers[0] : config.key}
        if len(config.headers) > 1:
            for key in config.headers[1:]:
                default_data[key] = ''
        log.info(default_data)
        (status, new_data) = handle_results_execution(default_data,
                                                      config.results)
        if not status:
            log.error("NON-FATAL: Failed to collect data for record:")
            log.error("NON-FATAL: %s" % default_data)
            log.error("NON-FATAL: Adding empty entry to spreadsheet")

        default_data.update(new_data)
        add_record(table, default_data)
        return

    # NOTE: len(rs) > 0
    for rec in rs:
        log.info(rec.content)
        (status, new_data) = handle_results_execution(rec.content.copy(),
                                                      config.results)
        if not status:
            msg = "Failed to collect data for record: %s" % new_data
            log.error("NON-FATAL: %s" % msg)

        update_record(rec, new_data)
    return

def handle_results_execution(current_data, command_format):
    # NOTE: format command to run using execute_fmt and current record values
    (status, value_raw) = command_wrapper(current_data, command_format)

    if status is False:
        log.error(str(value_raw))
        return (False, {})

    # NOTE: status == True, so success
    # TODO: maybe make ',' configurable?
    new_data = parse_raw_values(value_raw)
    log.info("new data: %s" % new_data)
    return (True, new_data)

def parse_raw_values(value_raw, separator=','):
    """ Takes a raw string blob that represents one or more lines separated
    by '\\n', and key,value pairs separated by 'separator' and returns a
    dictionary of the { key : value } pairs..

    If the same 'key' is found more than once, the value is appended with a
    space, 'value1 value2'.

    Args:
        value_raw - string, blob of text with key,value pairs
        separator - string, how key,value pairs are separated.
    Returns:
        dict of key,value pairs
    """
    value_list = value_raw.split('\n')
    new_data = {}
    for key_value in value_list:
        f = key_value.split(separator)
        if len(f) > 1:
            k,v = f
            if k in new_data:
                new_data[k] += " "+v.strip()
            else:
                new_data[k] = v.strip()
    return new_data

def command_wrapper(current_data, command_format):
    # NOTE: setup pre-defined values available to all commands
    date_ts = time.strftime("%Y-%m-%dT%H:%M")
    date = time.strftime("%Y-%m-%d")
    ts = int(time.time())

    # NOTE: set missing data to 'blank' rather than 'None'
    args = current_data.copy()
    for k,v in args.iteritems():
        if v is None:
            args[k] = ''
    args.update({'ts' : ts, 'date_ts' : date_ts, 'date' : date})

    command_format = command_format.replace("{", "%(")
    command_format = command_format.replace("}", ")s")
    cmd = command_format % args
    p = subprocess.Popen(cmd,
                         shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    input_str=None
    (s_out, s_err) = p.communicate(input_str)

    log.info("STDOUT:"+ s_out.strip())
    log.info("STDERR:"+ s_err.strip())

    if p.returncode != 0:
        return (False, s_err)

    # NOTE: success!
    return (True, s_out)

def main():
    (config, args) = parse_args()

    # NOTE: setup connection to db & table
    client = spreadsheet_textdb.DatabaseClient(config.email, config.password)
    db = get_db(client, config.sheetname, config.create)
    table = get_table(db, config.table, config.columns, config.create)

    # NOTE: look up sheet column names for future reference
    if config.show or config.update:
        table.LookupFields()
        config.headers = table.fields

    # NOTE: process mutually exclusive options create, show, update, delete
    if config.create:
        # NOTE: all operations for create are processsed at this point.
        sys.exit(0)

    elif config.show:
        handle_show(table, config)
    
    elif config.update:
        handle_update(table, config)

    elif config.delete:
        # TODO: add delete
        log.error("TODO: implement --delete")
        sys.exit(1)

    sys.exit(0)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
