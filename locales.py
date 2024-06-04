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
            'ready': {
                'content': ['Be ready !', 'Hold on !'],
            },
            'cheese': {
                'content': ['Cheese!', 'Smile!'],
                'wait': 'Please wait ...',
                'error': 'Cannot trigger camera.',
            },
            'capture': {
                'title': 'Photo {} on {}',
                'save': 'Save',
                'trash': 'Trash',
            },
            'processing': {
                'content': ['Processing...', 'Still processing...', 'Almost done...', 'Any second now...'],
            },
            'save': {
                'title': 'Do you want to save this collage ?',
                'save': 'Save',
                'trash': 'Trash',
            },
            'print': {
                'title': 'Do you want to print this collage ?',
                'one_copy': 'One copy',
                'two_copies': 'Two copies',
                'three_copies': 'Three copies',
                'no': 'Ignore',
            },
            'printing': {
                'content': ['Resizing...', 'Montaging...', 'Compositing...', 'Printing...'],
                'error': 'Cannot print collage.\nDon\'t worry, collage has been saved ;)',
            },
            'success': {
                'content': ['Perfect !', 'Awesome !', 'Wahou !'],
            },
            'copying': {
                'content': 'Copying to USB dongle\nDo not remove or turn off !',
            },
        }
    
    @staticmethod
    def get_FR(self):
        return {
            'waiting': {
                'action': 'Appuyez pour démarrer',
                'version': 'Version 1.0',
            },
            'select_format': {
                'title': 'Selectionnez le format de sortie',
            },
            'error': {
                'default': 'Une erreur s\'est produite.\nApouyez pour continuer.',
                'content': '{}\nApouyez pour continuer.',
            },
            'ready': {
                'content': ['Prêts ?', 'Parés ?', 'Au taquet ?'],
            },
            'cheese': {
                'content': ['Souriez !', 'Cheese !'],
                'wait': 'Veuillez patienter ...',
                'error': 'Impossible de prendre la photo.',
            },
            'capture': {
                'title': 'Photo {} sur {}',
                'save': 'Sauver',
                'trash': 'Refaire',
            },
            'processing': {
                'content': ['Traitement en cours ...', 'Ça mouline toujours ...', 'On y est presque ...', 'Encore un peu de patience ...'],
            },
            'save': {
                'title': 'Voulez-vous sauvegarder ce montage ?',
                'save': 'Sauver',
                'trash': 'Non',
            },
            'print': {
                'title': 'Voulez-vous imprimer ce montage ?',
                'one_copy': 'Imprimer 1 fois',
                'two_copies': 'Imprimer 2 fois',
                'three_copies': 'Imprimer 3 fois',
                'no': 'Ignore',
            },
            'printing': {
                'content': ['Impression en cours ...', 'Patience ...', 'Ça arrive ...', 'On y est presque ...'],
                'error': 'Impossible d\'imprimer l\'image.\nElle a quand même été sauvegardée ;)',
            },
            'success': {
                'content': ['Parfait !', 'Merci !', 'Wahou !', 'Trop classe !'],
            },
            'copying': {
                'content': 'Transfert des photos sur le support USB.\nNe le retirez pas jusqu\'à ce que cet écran disparaisse !',
            },
        }
