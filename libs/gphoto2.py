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
        message = gp.gp_result_as_string(result)
        raise libgphoto2error(result, message)
    return result

def check_unref(result, camfile):
    if result!=0:
        gp.gp_file_unref(camfile._cf)
        gp.gp_result_as_string.restype = ctypes.c_char_p
        message = gp.gp_result_as_string(result)
        raise libgphoto2error(result, message)
    
class cameraList():
    def __init__(self):
        self._l = ctypes.c_void_p()
        if not hasattr(gp, 'gp_camera_autodetect'): raise Exception('gphoto2 version is obsolete.')
        gp.gp_camera_autodetect(self._l, context)

    def get(self):
        return [(self._get_name(i), self._get_value(i)) for i in range(self.count())]

    def count(self):
        return check(gp.gp_list_count(self._l))

    def _get_name(self, index):
        name = ctypes.c_char_p()
        check(gp.gp_list_get_name(self._l, int(index), PTR(name)))
        return name.value
    
    def _get_value(self, index):
        value = ctypes.c_char_p()
        check(gp.gp_list_get_value(self._l, int(index), PTR(value)))
        return value.value

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
        check(gp.gp_camera_get_config(self._cam, PTR(config._w), context))
        config.populate_children()
        return config

    def _set_config(self, config):
        check(gp.gp_camera_set_config(self._cam, config._w, context))

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
        self._w = ctypes.c_void_p()

    def ref(self):
        check(gp.gp_widget_ref(self._w))

    def unref(self):
        check(gp.gp_widget_unref(self._w))

    def __del__(self):
        self.unref()

    def _get_info(self):
        info = ctypes.c_char_p()
        check(gp.gp_widget_get_info(self._w, PTR(info)))
        return info.value
    
    def _set_info(self, info):
        check(gp.gp_widget_set_info(self._w, str(info)))

    def _get_name(self):
        name = ctypes.c_char_p()
        check(gp.gp_widget_get_name(self._w, PTR(name)))
        return name.value
    
    def _set_name(self, name):
        check(gp.gp_widget_set_name(self._w, str(name)))

    def _get_id(self):
        id = ctypes.c_int()
        check(gp.gp_widget_get_id(self._w, PTR(id)))
        return id.value
    
    def _set_changed(self, changed):
        check(gp.gp_widget_set_changed(self._w, str(changed)))

    def _get_changed(self):
        return gp.gp_widget_changed(self._w)

    def _get_readonly(self):
        readonly = ctypes.c_int()
        check(gp.gp_widget_get_readonly(self._w, PTR(readonly)))
        return readonly.value
    
    def _set_readonly(self, readonly):
        check(gp.gp_widget_set_readonly(self._w, int(readonly)))

    def _get_type(self):
        type = ctypes.c_int()
        check(gp.gp_widget_get_type(self._w, PTR(type)))
        return type.value

    def _get_label(self):
        label = ctypes.c_char_p()
        check(gp.gp_widget_get_label(self._w, PTR(label)))
        return label.value
    
    def _set_label(self, label):
        check(gp.gp_widget_set_label(self._w, str(label)))

    def _get_value(self):
        value = ctypes.c_void_p()
        ans = gp.gp_widget_get_value(self._w, PTR(value))
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
        check(gp.gp_widget_set_value(self._w, value))

    def count_children(self):
        return gp.gp_widget_count_children(self._w)

    def get_child(self, child_number):
        w = cameraConfig()
        check(gp.gp_widget_get_child(self._w, int(child_number), PTR(w._w)))
        check(gp.gp_widget_ref(w._w))
        return w

    def get_child_by_label(self, label):
        w = cameraConfig()
        check(gp.gp_widget_get_child_by_label(self._w, str(label), PTR(w._w)))
        return w

    def get_child_by_id(self, id):
        w = cameraConfig()
        check(gp.gp_widget_get_child_by_id(self._w, int(id), PTR(w._w)))
        return w

    def get_child_by_name(self, name):
        w = cameraConfig()
        # this fails in 2.4.6 (Ubuntu 9.10)
        check(gp.gp_widget_get_child_by_name(self._w, str(name), PTR(w._w)))
        return w

    def _get_children(self):
        children = []
        for i in range(self.count_children()):
            children.append(self.get_child(i))
        return children
    
    def _get_parent(self):
        w = cameraConfig()
        check(gp.gp_widget_get_parent(self._w, PTR(w._w)))
        return w

    def _get_root(self):
        w = cameraConfig()
        check(gp.gp_widget_get_root(self._w, PTR(w._w)))
        return w

    def _set_range(self, range):
        """cameraConfig.range = (min, max, increment)"""
        float = ctypes.c_float
        min, max, increment = range
        check(gp.gp_widget_set_range(self._w, float(min), float(max), float(increment)))
    
    def _get_range(self, range):
        """cameraConfig.range => (min, max, increment)"""
        min, max, increment = ctypes.c_float(), ctypes.c_float(), ctypes.c_float()
        check(gp.gp_widget_set_range(self._w, PTR(min), PTR(max), PTR(increment)))
        return (min.value, max.value, increment.value)

    def createdoc(self):
        label = "Label: {}".format(str(self.label))
        info = "Info: {}".format(str(self.info if str(self.info) != "" else "n/a"))
        type = "Type: {}".format(str(self.typestr))
        #value = "Current value: {}".format(str(self.value))
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
            simplechild = cameraConfigRow()
            if c.count_children():
                setattr(simplewidget, c.name, simplechild)
                simplechild.__doc__ = c.createdoc()
                c._pop(simplechild)
            else:
                setattr(simplewidget, c.name, c)

            #print(c.name, simplewidget.__doc__)
        #print(dir(simplewidget))

    def populate_children(self):
        simplewidget = cameraConfigRow()
        setattr(self, self.name, simplewidget)
        simplewidget.__doc__ = self.createdoc()
        self._pop(simplewidget)

    def __repr__(self):
        return "%s:%s:%s:%s:%s" % (self.label, self.name, self.info, self.typestr, self.value)
    
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

class cameraConfigRow():
    pass