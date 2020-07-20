def get_var(substr):
    temp=[]
    body = []
    key = None
    value = None
    for c in substr:
        if key is None:
            if c == b'='[0] :
                key = ''.join([chr(b) for b in temp])
            else:
                temp.append(c) 
        else:
            body.append(c)
            
    value = ''.join([chr(b) for b in body])
    return key,value

def get_post_variable(request):
    var = {}

    req = request.strip(b'\0')
    reqs = req.split(b'&')

    for v in reqs:
        key,value = get_var(v)
        if key is not None:
            var[key] = value
    return var

table = []
table_reverse = []


def init_tables(poly, reverse=True):
    global table, table_reverse
    table = []
    # build CRC32 table
    for i in range(256):
        for j in range(8):
            if i & 1:
                i >>= 1
                i ^= poly
            else:
                i >>= 1
        table.append(i)
    assert len(table) == 256, "table is wrong size"
    # build reverse table
    if reverse:
        table_reverse = []
        found_none = set()
        found_multiple = set()
        for i in range(256):
            found = []
            for j in range(256):
                if table[j] >> 24 == i:
                    found.append(j)
            table_reverse.append(tuple(found))
            if not found:
                found_none.add(i)
            elif len(found) > 1:
                found_multiple.add(i)
        assert len(table_reverse) == 256, "reverse table is wrong size"
        if found_multiple:
            logging.warn('Multiple table entries have an MSB in {0}'.format(
                rangess(found_multiple)))
        if found_none:
            logging.error('no MSB in the table equals bytes in {0}'.format(
                rangess(found_none)))

def reverseBits(x):
    # http://graphics.stanford.edu/~seander/bithacks.html#ReverseParallel
    # http://stackoverflow.com/a/20918545
    x = ((x & 0x55555555) << 1) | ((x & 0xAAAAAAAA) >> 1)
    x = ((x & 0x33333333) << 2) | ((x & 0xCCCCCCCC) >> 2)
    x = ((x & 0x0F0F0F0F) << 4) | ((x & 0xF0F0F0F0) >> 4)
    x = ((x & 0x00FF00FF) << 8) | ((x & 0xFF00FF00) >> 8)
    x = ((x & 0x0000FFFF) << 16) | ((x & 0xFFFF0000) >> 16)
    return x & 0xFFFFFFFF

def crc32(data, accum=0,poly=0x04C11DB7):

    if len(table) == 0:
        init_tables(poly=reverseBits(poly),reverse=False)

    accum = ~accum
    for b in data:
        accum = table[(accum ^ b) & 0xFF] ^ ((accum >> 8) & 0x00FFFFFF)
    accum = ~accum
    return accum & 0xFFFFFFFF

if __name__ == "__main__":
    var = get_post_variable(b'&ip=fd00::212:4b00:1005:fdf3&opt=2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')    
    print(var)