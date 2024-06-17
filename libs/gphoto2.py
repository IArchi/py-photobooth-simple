import os
import time
import ctypes

RETRIES = 1
GP_CAPTURE_IMAGE = 0
GP_FILE_TYPE_NORMAL = 1

gp = ctypes.CDLL('libgphoto2.so')
PTR = ctypes.pointer
context = gp.gp_context_new()

class libgphoto2error(Exception):
    def __init__(self, result, message):
        self.result = result
        self.message = message
    def __str__(self):
        return self.message + ' (' + str(self.result) + ')'

class CameraFilePath(ctypes.Structure):
    _fields_ = [('name', (ctypes.c_char * 128)), ('folder', (ctypes.c_char * 1024))]

class CameraText(ctypes.Structure):
    _fields_ = [('text', (ctypes.c_char * (32 * 1024)))]

def check(result):
    if result < 0:
        gp.gp_result_as_string.restype = ctypes.c_char_p
        message = str(gp.gp_result_as_string(result), encoding='ascii')
        raise libgphoto2error(result, message)
    return result


def check_unref(result, camfile):
    if result != 0:
        gp.gp_file_unref(camfile.pointer)
        gp.gp_result_as_string.restype = ctypes.c_char_p
        message = gp.gp_result_as_string(result)
        raise libgphoto2error(result, message)

class cameraList():
    def __init__(self):
        self._ptr = ctypes.c_void_p()
        check(gp.gp_list_new(PTR(self._ptr)))
        if not hasattr(gp, 'gp_camera_autodetect'): raise Exception('gphoto2 version is obsolete.')
        gp.gp_camera_autodetect(self._ptr, context)

    def get(self):
        return [(self._get_name(i), self._get_value(i)) for i in range(self.count())]

    def count(self):
        return check(gp.gp_list_count(self._ptr))

    def _get_name(self, index):
        name = ctypes.c_char_p()
        check(gp.gp_list_get_name(self._ptr, int(index), PTR(name)))
        return str(name.value, encoding='ascii')

    def _get_value(self, index):
        value = ctypes.c_char_p()
        check(gp.gp_list_get_value(self._ptr, int(index), PTR(value)))
        return str(value.value, encoding='ascii')

class camera():
    def __init__(self, autoInit = True):
        self._cam = ctypes.c_void_p()
        self._leave_locked = False
        check(gp.gp_camera_new(PTR(self._cam)))
        self.initialized = False
        self._init()

    def __del__(self):
        if not self._leave_locked:
            check(gp.gp_camera_exit(self._cam))
            check(gp.gp_camera_free(self._cam))

    def summary(self):
        txt = CameraText()
        check(gp.gp_camera_get_summary(self._cam, PTR(txt), context))
        return txt.text

    def leave_locked(self):
        self._leave_locked = True

    def _get_config(self):
        config = cameraConfig()
        check(gp.gp_camera_get_config(self._cam, PTR(config._ptr), context))
        config.populate_children()
        return config

    def _set_config(self, config):
        check(gp.gp_camera_set_config(self._cam, config._ptr, context))

    config = property(_get_config, _set_config)

    def capture_image(self, destpath=None):
        # Triffer capture
        path = CameraFilePath()
        ans = 0
        for _ in range(1 + RETRIES):
            ans = gp.gp_camera_capture(self._cam, GP_CAPTURE_IMAGE, PTR(path), context)
            if ans == 0: break
        check(ans)
        cfile = cameraFile(self._cam, path.folder, path.name)

        # Save to file
        if destpath:
            cfile.save(destpath.encode('ascii'))
            cfile.unref()
            cfile.clean()
        else:
            return cfile

    def capture_preview(self, destpath=None):
        # Trigger capture
        path = CameraFilePath()
        cfile = cameraFile()
        ans = 0
        for _ in range(1 + RETRIES):
            ans = gp.gp_camera_capture_preview(self._cam, cfile._cf, context)
            if ans == 0: break
        check(ans)

        # Save to file
        if destpath:
            cfile.save(destpath.encode('ascii'))
            cfile.unref()
            cfile.clean()
        else:
            return cfile

    def trigger_capture(self):
        check(gp.gp_camera_trigger_capture(self._cam, context))

    def _init(self):
        ans = 0
        for i in range(1 + RETRIES):
            ans = gp.gp_camera_init(self._cam, context)
            # Success
            if ans == 0: break

            # Error (Could not lock the device)
            elif ans == -60:
                os.system('gvfs-mount -s gphoto2')
                time.sleep(1)
        check(ans)
        self.initialized = True

class cameraFile():
    def __init__(self, cam = None, srcfolder = None, srcfilename = None):
        self._cf = ctypes.c_void_p()
        check(gp.gp_file_new(PTR(self._cf)))
        if cam: check_unref(gp.gp_camera_file_get(cam, srcfolder, srcfilename, GP_FILE_TYPE_NORMAL, self._cf, context), self)

    def open(self, filename):
        check(gp.gp_file_open(PTR(self._cf), filename))

    def save(self, filename=None):
        if filename is None: filename = self.name
        check(gp.gp_file_save(self._cf, filename))

    def ref(self):
        check(gp.gp_file_ref(self._cf))

    def unref(self):
        check(gp.gp_file_unref(self._cf))

    def clean(self):
        check(gp.gp_file_clean(self._cf))

class cameraConfig():
    def __init__(self):
        self._ptr = ctypes.c_void_p()

    def ref(self):
        check(gp.gp_widget_ref(self._ptr))

    def unref(self):
        check(gp.gp_widget_unref(self._ptr))

    def __del__(self):
        self.unref()

    def _get_info(self):
        info = ctypes.c_char_p()
        check(gp.gp_widget_get_info(self._ptr, PTR(info)))
        return info.value

    def _set_info(self, info):
        check(gp.gp_widget_set_info(self._ptr, str(info)))

    def _get_name(self):
        name = ctypes.c_char_p()
        check(gp.gp_widget_get_name(self._ptr, PTR(name)))
        return name.value

    def _set_name(self, name):
        check(gp.gp_widget_set_name(self._ptr, str(name)))

    def _get_id(self):
        id = ctypes.c_int()
        check(gp.gp_widget_get_id(self._ptr, PTR(id)))
        return id.value

    def _set_changed(self, changed):
        check(gp.gp_widget_set_changed(self._ptr, str(changed)))

    def _get_changed(self):
        return gp.gp_widget_changed(self._ptr)

    def _get_readonly(self):
        readonly = ctypes.c_int()
        check(gp.gp_widget_get_readonly(self._ptr, PTR(readonly)))
        return readonly.value

    def _set_readonly(self, readonly):
        check(gp.gp_widget_set_readonly(self._ptr, int(readonly)))

    def _get_type(self):
        type = ctypes.c_int()
        check(gp.gp_widget_get_type(self._ptr, PTR(type)))
        return type.value

    def _get_label(self):
        label = ctypes.c_char_p()
        check(gp.gp_widget_get_label(self._ptr, PTR(label)))
        return label.value

    def _set_label(self, label):
        check(gp.gp_widget_set_label(self._ptr, str(label)))

    def _get_value(self):
        value = ctypes.c_void_p()
        ans = gp.gp_widget_get_value(self._ptr, PTR(value))
        if self.type in [2, 5, 6]: value = ctypes.cast(value.value, ctypes.c_char_p)
        elif self.type == 3: value = ctypes.cast(value.value, ctypes.c_float_p)
        elif self.type in [4, 8]:
            #value = ctypes.cast(value.value, ctypes.c_int_p)
            pass
        else: return None
        check(ans)
        return value.value

    def _set_value(self, value):
        if self.type in [2, 5, 6]: value = ctypes.c_char_p(value)
        elif self.type == 3: value = ctypes.c_float_p(value)
        elif self.type in [4, 8]: value = PTR(ctypes.c_int(value)) # c_int_p ? TODO
        else: return
        check(gp.gp_widget_set_value(self._ptr, value))

    def count_children(self):
        return gp.gp_widget_count_children(self._ptr)

    def get_child(self, child_number):
        w = cameraConfig()
        check(gp.gp_widget_get_child(self._ptr, int(child_number), PTR(w._ptr)))
        check(gp.gp_widget_ref(w._ptr))
        return w

    def get_child_by_label(self, label):
        w = cameraConfig()
        check(gp.gp_widget_get_child_by_label(self._ptr, str(label), PTR(w._ptr)))
        return w

    def get_child_by_id(self, id):
        w = cameraConfig()
        check(gp.gp_widget_get_child_by_id(self._ptr, int(id), PTR(w._ptr)))
        return w

    def get_child_by_name(self, name):
        w = cameraConfig()
        # this fails in 2.4.6 (Ubuntu 9.10)
        check(gp.gp_widget_get_child_by_name(self._ptr, str(name), PTR(w._ptr)))
        return w

    def _get_children(self):
        children = []
        for i in range(self.count_children()):
            children.append(self.get_child(i))
        return children

    def _get_parent(self):
        w = cameraConfig()
        check(gp.gp_widget_get_parent(self._ptr, PTR(w._ptr)))
        return w

    def _get_root(self):
        w = cameraConfig()
        check(gp.gp_widget_get_root(self._ptr, PTR(w._ptr)))
        return w

    def _set_range(self, range):
        """cameraConfig.range = (min, max, increment)"""
        float = ctypes.c_float
        min, max, increment = range
        check(gp.gp_widget_set_range(self._ptr, float(min), float(max), float(increment)))

    def _get_range(self, range):
        """cameraConfig.range => (min, max, increment)"""
        min, max, increment = ctypes.c_float(), ctypes.c_float(), ctypes.c_float()
        check(gp.gp_widget_set_range(self._ptr, PTR(min), PTR(max), PTR(increment)))
        return (min.value, max.value, increment.value)

    def createdoc(self):
        label = "Label: {}".format(str(self.label, encoding='ascii'))
        info = "Info: {}".format(str(self.info, encoding='ascii') if str(self.info, encoding='ascii') != "" else "n/a")
        type = "Type: {}".format(str(self.typestr, encoding='ascii'))
        #value = "Current value: {}".format(str(self.value, encoding='ascii'))
        childs = []
        for c in self.children: childs.append("  - {}: {}".format(str(c.name), str(c.label)))
        if len(childs):
            childstr = "Children:\n" + "\n".join(childs)
            return label + "\n" + info + "\n" + type + "\n" + childstr
        else:
            return label + "\n" + info + "\n" + type

    def _pop(widget, simplewidget):
        #print(widget)
        for c in widget.children:
            simplechild = cameraConfigChild()
            if c.count_children():
                setattr(simplewidget, str(c.name, encoding='ascii'), simplechild)
                simplechild.__doc__ = c.createdoc()
                c._pop(simplechild)
            else:
                setattr(simplewidget, str(c.name, encoding='ascii'), c)

    def populate_children(self):
        simplechild = cameraConfigChild()
        setattr(self, str(self.name, encoding='ascii'), simplechild)
        simplechild.__doc__ = self.createdoc()
        self._pop(simplechild)

    def __str__(self):
        return getattr(self, str(self.name, encoding='ascii')).get_tree_structure()

    def __repr__(self):
        return "%s:%s:%s:%s:%s" % (str(self.label, encoding='ascii'), str(self.name, encoding='ascii'), str(self.info, encoding='ascii'), str(self.typestr, encoding='ascii'), str(self.value, encoding='ascii'))

    info = property(_get_info, _set_info)
    name = property(_get_name, _set_name)
    id = property(_get_id, None)
    changed = property(_get_changed, _set_changed)
    readonly = property(_get_readonly, _set_readonly)
    type = property(_get_type, None)
    label = property(_get_label, _set_label)
    value = property(_get_value, _set_value)
    children = property(_get_children, None)
    parent = property(_get_parent, None)
    root = property(_get_root, None)
    range = property(_get_range, _set_range)

class cameraConfigChild():
    def __str__(self):
        return self.__doc__
    
    def get_tree_structure(self, indent=0):
        tree_structure = ' ' * indent + str(self.name, encoding='ascii') + '\n'
        for child_name, child_value in self.__dict__.items():
            if isinstance(child_value, cameraConfigChild):
                tree_structure += child_value.get_tree_structure(indent + 4)
            else:
                tree_structure += ' ' * (indent + 4) + str(child_value) + '\n'
        return tree_structure
