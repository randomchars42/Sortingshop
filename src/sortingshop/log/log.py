#!/usr/bin/env python3

config = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'simple': {
            'format': '%(asctime)s %(module)s %(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'loggers': {
        '__main__': {
            'handlers': ['console'],
            'propagate': False,
            'level':'DEBUG',
        },
        'sortingshop': {
            'handlers': ['console'],
            'propagate': False,
            'level':'DEBUG',
        },
        'sortingshop.ui': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}
