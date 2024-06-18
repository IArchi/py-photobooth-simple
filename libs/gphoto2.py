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
    def __init__(self):
        self._ptr = ctypes.c_void_p()
        check(gp.gp_camera_new(PTR(self._ptr)))
        self._init()

    def __del__(self):
        check(gp.gp_camera_exit(self._ptr))
        check(gp.gp_camera_free(self._ptr))

    def close(self):
        check(gp.gp_camera_exit(self._ptr, context))

    def summary(self):
        txt = CameraText()
        check(gp.gp_camera_get_summary(self._ptr, PTR(txt), context))
        summary = str(txt.text, encoding='ascii')
        r = {}
        for l in summary.splitlines():
            try:
                k, v = l.split(':')
            except ValueError:
                continue
            r[k.strip()] = v.strip()
        return summary

    def get_config(self):
        config = cameraConfig()
        check(gp.gp_camera_get_config(self._ptr, PTR(config._ptr), context))
        return config

    def commit_config(self, config):
        check(gp.gp_camera_set_config(self._ptr, config._ptr, context))

    def capture_image(self, destpath=None):
        # Triffer capture
        path = CameraFilePath()
        ans = 0
        for _ in range(1 + RETRIES):
            ans = gp.gp_camera_capture(self._ptr, GP_CAPTURE_IMAGE, PTR(path), context)
            if ans == 0: break
        check(ans)
        cfile = cameraFile(self._ptr, path.folder, path.name)

        # Save to file
        if destpath:
            cfile.save(destpath.encode('ascii'))
            cfile.unref()
            cfile.clean()
            return None
        else:
            return cfile

    def capture_preview(self, destpath=None):
        # Trigger capture
        path = CameraFilePath()
        cfile = cameraFile()
        ans = 0
        for _ in range(1 + RETRIES):
            ans = gp.gp_camera_capture_preview(self._ptr, cfile._ptr, context)
            if ans == 0: break
        check(ans)

        # Save to file
        if destpath:
            cfile.save(destpath.encode('ascii'))
            cfile.unref()
            cfile.clean()
            return None
        else:
            return cfile

    def trigger_capture(self):
        check(gp.gp_camera_trigger_capture(self._ptr, context))

    def _init(self):
        ans = 0
        for i in range(1 + RETRIES):
            ans = gp.gp_camera_init(self._ptr, context)
            # Success
            if ans == 0: break

            # Error (Could not lock the device)
            elif ans == -60:
                os.system('gvfs-mount -s gphoto2')
                time.sleep(1)
        check(ans)

class cameraFile():
    def __init__(self, cam = None, srcfolder = None, srcfilename = None):
        self._ptr = ctypes.c_void_p()
        check(gp.gp_file_new(PTR(self._ptr)))
        if cam: check_unref(gp.gp_camera_file_get(cam, srcfolder, srcfilename, GP_FILE_TYPE_NORMAL, self._ptr, context), self)

    def open(self, filename):
        check(gp.gp_file_open(PTR(self._ptr), filename))

    def get_data(self, auto_clean=True):
        data = ctypes.c_char_p()
        size = ctypes.c_ulong()
        check(gp.gp_file_get_data_and_size(self._ptr, PTR(data), PTR(size)))
        data = ctypes.string_at(data, int(size.value))
        if auto_clean:
            self.unref()
            self.clean()
        return data

    def save(self, filename=None):
        if filename is None: filename = self.name
        check(gp.gp_file_save(self._ptr, filename))

    def ref(self):
        check(gp.gp_file_ref(self._ptr))

    def unref(self):
        check(gp.gp_file_unref(self._ptr))

    def clean(self):
        check(gp.gp_file_clean(self._ptr))

class cameraConfig():
    def __init__(self):
        self._ptr = ctypes.c_void_p()

    def ref(self):
        check(gp.gp_widget_ref(self._ptr))

    def unref(self):
        check(gp.gp_widget_unref(self._ptr))

    def __del__(self):
        self.unref()

    def get_path(self, path):
        names = path.strip('/').split('/')
        current_widget = self
        for name in names:
            if name == 'main': continue
            current_widget = current_widget._get_child_by_name(name)
            if current_widget is None: return None
        return current_widget

    def list_paths(self, parent_path="/main"):
        children_paths = []
        children = self._get_children()
        for child in children:
            child_path = f"{parent_path}/{child.get_name()}"
            if child._count_children() == 0: children_paths.append(child_path)
            children_paths.extend(child.list_paths(child_path))
        return children_paths

    def get_label(self):
        label = ctypes.c_char_p()
        check(gp.gp_widget_get_label(self._ptr, PTR(label)))
        return str(label.value, encoding='ascii')

    def get_info(self):
        info = ctypes.c_char_p()
        check(gp.gp_widget_get_info(self._ptr, PTR(info)))
        return str(info.value, encoding='ascii')

    def get_type(self):
        type = ctypes.c_int()
        check(gp.gp_widget_get_type(self._ptr, PTR(type)))
        return type.value

    def get_value(self):
        type = self.get_type()
        value = ctypes.c_void_p()
        ans = gp.gp_widget_get_value(self._ptr, PTR(value))
        check(ans)
        if type in [2, 5, 6]:
            value = ctypes.cast(value.value, ctypes.c_char_p)
            return str(value.value, encoding='ascii')
        elif type == 3:
            value = ctypes.cast(value.value, ctypes.c_float_p)
            return value.value
        elif type in [4, 8]:
            value = ctypes.cast(value.value, ctypes.c_int_p)
            return value.value
        else:
            return None

    def set_value(self, value):
        type = self.get_type()
        if type in [2, 5, 6]:
            if isinstance(value, str): value = str.encode(value)
            if not isinstance(value, bytes): raise libgphoto2error(type(value).__name__, 'Value should either be a string or bytes')
            value = ctypes.c_char_p(value)
        elif type == 3:
            if isinstance(value, str): value = float(value)
            value = ctypes.c_float_p(value)
        elif type in [4, 8]:
            if isinstance(value, str): value = int(value)
            value = PTR(ctypes.c_int(value)) # c_int_p ? TODO
        else: return
        check(gp.gp_widget_set_value(self._ptr, value))

    def get_name(self):
        name = ctypes.c_char_p()
        check(gp.gp_widget_get_name(self._ptr, PTR(name)))
        return str(name.value, encoding='ascii')

    def _get_child_by_name(self, name):
        for i in range(self._count_children()):
            child = cameraConfig()
            check(gp.gp_widget_get_child(self._ptr, int(i), PTR(child._ptr)))
            check(gp.gp_widget_ref(child._ptr))
            if child.get_name() == name: return child
        return None

    def _count_children(self):
        return gp.gp_widget_count_children(self._ptr)

    def _get_children(self):
        children = []
        for i in range(self._count_children()):
            child = cameraConfig()
            check(gp.gp_widget_get_child(self._ptr, int(i), PTR(child._ptr)))
            check(gp.gp_widget_ref(child._ptr))
            children.append(child)
        return children
