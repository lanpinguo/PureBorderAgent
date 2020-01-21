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

if __name__ == "__main__":
    var = get_post_variable(b'&ip=fd00::212:4b00:1005:fdf3&opt=2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')    
    print(var)