import bpy


class TranslationHelper():
    def __init__(self, name: str, data: dict, lang='zh_CN'):
        self.name = name
        self.translations_dict = dict()

        for src, src_trans in data.items():
            key = ("Operator", src)
            self.translations_dict.setdefault(lang, {})[key] = src_trans
            key = ("*", src)
            self.translations_dict.setdefault(lang, {})[key] = src_trans

    def register(self):
        try:
            bpy.app.translations.register(self.name, self.translations_dict)
        except(ValueError):
            pass

    def unregister(self):
        bpy.app.translations.unregister(self.name)


# Set
############
from . import zh_HANS

zh_CN = TranslationHelper('light_helper_zh_CN', zh_HANS.data)
zh_HANS = TranslationHelper('light_helper_zh_HANS', zh_HANS.data, lang='zh_HANS')


def register():
    if bpy.app.version < (4, 0, 0):
        zh_CN.register()
    else:
        zh_CN.register()
        zh_HANS.register()


def unregister():
    if bpy.app.version < (4, 0, 0):
        zh_CN.unregister()
    else:
        zh_CN.unregister()
        zh_HANS.unregister()
