
REGISTER_BIT_COUNT = 8
REGISTER_MAX_VALUE = 2**REGISTER_BIT_COUNT - 1


REGISTERS = {
    0: {
        'NAME': 'RA',
        'MAX_VALUE': REGISTER_MAX_VALUE,
        'READABLE': True,
        'WRITABLE': True
    },
    1: {
        'NAME': 'RB',
        'MAX_VALUE': REGISTER_MAX_VALUE,
        'READABLE': True,
        'WRITABLE': True
    },
    2: {
        'NAME': 'RD',
        'MAX_VALUE': REGISTER_MAX_VALUE,
        'READABLE': True,
        'WRITABLE': True
    },
    3:{
        'NAME': 'MARL',
        'MAX_VALUE': 255,
        'READABLE': False,
        'WRITABLE': True
    },
    4:{
        'NAME': 'MARH',
        'MAX_VALUE': 255,
        'READABLE': False,
        'WRITABLE': True
    },
    5: {
        'NAME': 'ACC',
        'MAX_VALUE': REGISTER_MAX_VALUE,
        'READABLE': True,
        'WRITABLE': False
    },
    6: {
        'NAME': 'PRL',
        'MAX_VALUE': REGISTER_MAX_VALUE,
        'READABLE': False,
        'WRITABLE': True
    },
    7: {
        'NAME': 'PRH',
        'MAX_VALUE': REGISTER_MAX_VALUE,
        'READABLE': False,
        'WRITABLE': True
    },
    8: {
        'NAME': 'PCL',
        'MAX_VALUE': REGISTER_MAX_VALUE,
        'READABLE': True,
        'WRITABLE': False
    },
    9: {
        'NAME': 'PCH',
        'MAX_VALUE': REGISTER_MAX_VALUE,
        'READABLE': True,
        'WRITABLE': False
    }
}
