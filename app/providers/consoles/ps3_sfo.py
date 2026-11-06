import struct

FMT_UTF8=0x0204
FMT_UTF8_ALT=0x0004
FMT_INT32=0x0404

def parse_sfo(data: bytes) -> dict:
    if len(data) < 20 or data[:4] != b'\x00PSF':
        raise ValueError('Invalid PARAM.SFO')
    _, key_off, data_off, count = struct.unpack_from('<4sIIII', data, 0)
    out={}
    for i in range(count):
        pos=20+i*16
        if pos+16>len(data): break
        key_rel,fmt,length,max_len,val_rel=struct.unpack_from('<HHIII',data,pos)
        ks=key_off+key_rel
        ke=data.find(b'\x00',ks)
        if ke<0: continue
        key=data[ks:ke].decode('utf-8','replace')
        raw=data[data_off+val_rel:data_off+val_rel+length]
        if fmt==FMT_INT32 and len(raw)>=4:
            val=struct.unpack_from('<I',raw,0)[0]
        else:
            val=raw.rstrip(b'\x00').decode('utf-8','replace').strip()
        out[key]=val
    return out
