# cython: language_level=3
from libc.stdio cimport *
from libc.string cimport *
from libc.stdlib cimport atoi, atof, malloc, free

IF UNAME_SYSNAME == "Windows":
    # Windows平台实现
    cdef extern from "stdio.h":
        char* fgets(char* str, int num, FILE* stream)
    
    cdef size_t windows_getline(char** lineptr, size_t* n_ptr, FILE* stream):
        cdef:
            size_t current_size = n_ptr[0] if n_ptr else 0
            char* current_line = lineptr[0] if lineptr else NULL
            size_t pos = 0
            char* new_line

        if lineptr == NULL or n_ptr == NULL or stream == NULL:
            return -1

        if current_line == NULL or current_size == 0:
            current_size = 128
            current_line = <char*>malloc(current_size)
            if current_line == NULL:
                return -1
            lineptr[0] = current_line
            n_ptr[0] = current_size

        while True:
            if pos + 1 >= current_size:
                current_size *= 2
                new_line = <char*>realloc(current_line, current_size)
                if new_line == NULL:
                    free(current_line)
                    lineptr[0] = NULL
                    n_ptr[0] = 0
                    return -1
                current_line = new_line
                lineptr[0] = current_line
                n_ptr[0] = current_size

            if fgets(current_line + pos, <int>(current_size - pos), stream) == NULL:
                if pos == 0:
                    free(current_line)
                    lineptr[0] = NULL
                    n_ptr[0] = 0
                    return -1
                break

            pos += strlen(current_line + pos)
            if current_line[pos - 1] == '\n':
                break

        current_line[pos] = '\0'
        return pos

ELSE:
    # Unix/Linux平台实现
    cdef extern from "stdio.h":
        ssize_t getline(char** lineptr, size_t* n, FILE* stream)

def read_from_ldac_file(
        str filename, int N,
        int[:] dptr, int[:] wids, double[:] wcts):
    filename_byte_string = filename.encode("UTF-8")
    cdef char* fname = filename_byte_string
    cdef FILE* cfile
    cfile = fopen(fname, "rb")  # 统一使用二进制模式
    if cfile == NULL:
        raise IOError("File not found: '%s'" % filename)

    cdef:
        char* line = NULL
        size_t l = 0
        ssize_t read
        int n = 0
        int d = 1
        int N_d = 0

    try:
        while True:
            line = NULL
            l = 0

            IF defined(_WIN32) or defined(WIN32):
                read = windows_getline(&line, &l, cfile)
            ELSE:
                read = getline(&line, &l, cfile)

            if read == -1:
                break

            # 处理空行和换行符差异
            if line[0] == b'\r' or line[0] == b'\n':
                free(line)
                line = NULL
                continue

            # 解析文档内容（保持原有逻辑不变）
            N_d = atoi(line)
            line += 1
            while line[0] != 32:
                line += 1
            line += 1

            for tpos in range(0, N_d):
                wids[n] = atoi(line)
                line += 1
                while line[0] != 58:
                    line += 1
                line += 1

                wcts[n] = atof(line)
                if tpos < N_d - 1:
                    line += 1
                    while line[0] != 32:
                        line += 1
                    line += 1

                if n >= N:
                    raise IndexError("Provided N too small. n=%d" % (n))
                n += 1

            if d >= N:
                raise IndexError("Provided N too small for docs. d=%d" % (d))
            dptr[d] = n
            d += 1

            free(line)
            line = NULL

    except:
        if line != NULL:
            free(line)
        fclose(cfile)
        raise

    finally:
        if line != NULL:
            free(line)
        fclose(cfile)

    return n, d