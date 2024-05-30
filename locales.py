class Locales:
    @staticmethod
    def get_EN(self):
        return {
            'waiting': {
                'action': 'Press to begin',
                'version': 'Version 1.0',
            },
            'select_format': {
                'title': 'Select format',
            },
            'error': {
                'default': 'An error occured.\nClick to continue',
                'content': '{}\nClick to continue',
            },
            'cheese': {
                'content': ['Cheese!', 'Smile!'],
                'wait': 'Please wait ...',
                'error_args': 'An error occured !',
                'error_camera': 'Cannot trigger camera.',
            },
            'capture': {
                'title': 'Photo {} sur {}',
                'yes': 'Keep it ({})',
                'no': 'New take',
                'error_args': 'An error occured !',
            },
            'processing': {
                'content': ['Processing...', 'Still processing...', 'Almost done...', 'Any second now...'],
            },
            'save': {
                'title': 'Do you want to save this collage ?',
                'yes': 'Yes ({})',
                'no': 'No',
            },
            'print': {
                'title': 'Do you want to print this collage ?',
                'one_copy': 'One copy',
                'two_copies': 'Two copies',
                'three_copies': 'Three copies',
                'no': 'Ignore ({})',
            },
            'printing': {
                'content': ['Resizing...', 'Montaging...', 'Compositing...', 'Printing...'],
                'error': 'Cannot print collage.\nDon\'t worry, collage has been saved ;)',
            },
            'success': {
                'content': ['Perfect !', 'Awesome !', 'Wahou !'],
            },
        }
