class Locales:
    @staticmethod
    def get_EN(self):
        return {
            'waiting': {
                'action': 'Press to begin',
                'version': 'Version 1.0',
            },
            'select_format': {
                'title': 'Select output format',
            },
            'error': {
                'default': 'An error occured.\nClick to continue',
                'content': '{}\nClick to continue',
            },
            'ready': {
                'content': ['Be ready !', 'Hold on !'],
            },
            'cheese': {
                'content': ['Cheese !', 'Smile !'],
                'wait': 'Please wait ...',
                'error': 'Cannot trigger camera.',
            },
            'capture': {
                'title': 'Shot {} on {}',
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
                'print': 'Print',
                'one_copy': 'Print once',
                'two_copies': 'Print twice',
                'three_copies': 'Print three copies',
                'no': 'Ignore',
            },
            'printing': {
                'content': ['Printing...', 'Be patient...', 'Almost done...', 'Any second now...'],
                'error': 'Cannot print collage.\nDon\'t worry, collage has been saved ;)',
                'error_toolong': 'Printer might be stuck.',
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
                'title': 'Selectionnez le modèle',
            },
            'error': {
                'default': 'Une erreur s\'est produite.\nApouyez pour continuer.',
                'content': '{}\nApouyez pour continuer.',
            },
            'ready': {
                'content': ['Prêts ?', 'Parés ?'],
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
                'print': 'Imprimer',
                'one_copy': 'Imprimer\n1 fois',
                'two_copies': 'Imprimer\n2 fois',
                'no': 'Ignorer',
            },
            'printing': {
                'content': ['Impression en cours ...', 'Patience ...', 'Ça arrive ...', 'On y est presque ...'],
                'error': 'Impossible d\'imprimer l\'image.\nElle a quand même été sauvegardée ;)',
                'error_toolong': 'L\'imprimante est peut être bloquée.',
            },
            'success': {
                'content': ['Parfait !', 'Merci !', 'Wahou !', 'Trop classe !'],
            },
            'copying': {
                'content': 'Transfert des photos sur le support USB.\nNe le retirez pas jusqu\'à ce que cet écran disparaisse !',
            },
        }
