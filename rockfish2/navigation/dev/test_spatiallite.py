import sqlite3

con = sqlite3.connect(':memory:') 
#con.enable_load_extension(True) 
con.load_extension('libspatialiteprovider.so') 
con.execute('select InitSpatialMetadata()') 
for row in con.execute('select * from spatial_ref_sys'): 
    print row 
