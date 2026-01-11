
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
    }
}