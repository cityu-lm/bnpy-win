# setup.py 跨平台优化版
import os
import sys
from setuptools import setup, Extension
from distutils.sysconfig import customize_compiler

try:
    from Cython.Distutils import build_ext
    HAS_CYTHON = True
except ImportError:
    from distutils.command.build_ext import build_ext
    HAS_CYTHON = False

# 平台检测优化 (网页1)
is_windows = sys.platform.startswith('win')
is_macos = sys.platform.startswith('darwin')

def get_compile_args():
    args = []
    if is_windows:
        args += ['/std:c++14', '/O2']  # 强制C++14标准[4](@ref)
    else:
        args += ["-std=c++14", "-O3"]   # GCC/Clang兼容配置
    return args

def get_link_args():
    """ 跨平台链接参数优化 """
    args = []
    if is_windows:
        args += ['/NODEFAULTLIB:libcmt']  # 避免MSVC库冲突
    else:
        args += ["-lm", "-fopenmp"]
        if is_macos:
            args += ["-lc++"]  # macOS C++标准库
    return args

def get_define_macros():
    """ 平台宏定义传递到C/C++代码 """
    macros = []
    if is_windows:
        macros.append(('WIN32', '1'))
        macros.append(('_CRT_SECURE_NO_WARNINGS', '1'))  # 禁用MSVC安全警告
    return macros

def get_path_to_eigen():
    """ 多路径搜索策略 """
    candidate_paths = [
        os.environ.get('EIGENPATH', ''),
        '/usr/local/include/eigen3',  # Linux/macOS默认路径
        'C:\\Libs\\eigen3'  # Windows常见安装路径
    ]
    for path in candidate_paths:
        if os.path.exists(os.path.join(path, 'Eigen/Core')):
            return path
    return ''

def make_extensions():
    ''' 增强的扩展模块配置 '''
    common_settings = {
        'define_macros': get_define_macros(),
        'extra_compile_args': get_compile_args(),
        'extra_link_args': get_link_args(),
        'language': 'c++'  # 统一使用C++编译器(网页2)
    }
    
    ext_list = [
        make_cython_extension('SparseRespUtilX', **common_settings),
        make_cython_extension('EntropyUtilX', **common_settings),
        make_cython_extension('TextFileReaderX', **common_settings),
    ]
    
    # 条件编译增强(网页1)
    eigen_path = get_path_to_eigen()
    if eigen_path:
        ext_list += [
            make_cpp_extension(
                'libfwdbwdcpp',
                sources=['bnpy/allocmodel/hmm/lib/FwdBwdRowMajor.cpp'],
                include_dirs=[eigen_path],
                **common_settings
            ),
            make_cpp_extension(
                'libsparsemix',
                sources=['bnpy/util/lib/sparseResp/SparsifyRespCPPX.cpp'],
                include_dirs=[eigen_path],
                **common_settings
            )
        ]
    
    return ext_list

def make_cython_extension(name, **kwargs):
    """ 统一Cython扩展生成器 """
    return Extension(
        f"bnpy.util.{name}",
        sources=[f"bnpy/util/{name}.pyx"],
        **kwargs
    )

def make_cpp_extension(name, **kwargs):
    """ 统一C++扩展生成器 """
    return Extension(
        f"bnpy.util.lib.{name}",
        **kwargs
    )
    

class CustomizedBuildExt(build_ext):
    """ 增强的跨平台编译处理(网页2) """
    def build_extensions(self):
        # 编译器定制
        customize_compiler(self.compiler)
        
        # Windows特定处理
        if is_windows:
            self.compiler.compiler_so = [
                arg for arg in self.compiler.compiler_so 
                if not any(arg.startswith(flag) 
                for flag in ('-Wstrict-prototypes', '-g'))
            ]
            self.compiler.define_macro('WIN32', '1')
        
        # macOS特定处理
        if is_macos:
            self.compiler.compiler_so.append('-stdlib=libc++')
            self.compiler.compiler_so.append('-mmacosx-version-min=10.15')
        
        super().build_extensions()

# 依赖管理优化(网页1)
install_requires = [
    "Cython>=0.29",  # 保持原要求（网页5显示PyTorch 1.7.1支持3.7，间接验证兼容性）
    "numpy>=1.17,<1.21",  # Python3.7最高支持numpy1.20.x[1](@ref)
    "scipy>=1.3,<1.6",    # scipy1.6+需要Python3.8+
    "pandas>=0.25,<1.2",  # pandas1.2+需要Python3.8+
    "scikit-learn>=0.22", # 保持最低兼容版本
    "matplotlib>=3.3",    # 3.4+需要Python3.8+
]

extras_require = {
    'gpu': ["cupy>=10.0", "pyopencl"],
    'docs': ["sphinx>=4.0", "sphinx_rtd_theme"],
    'tests': ["pytest>=6.0", "coverage"],
    'all': ["cupy", "sphinx", "pytest"]
}

setup(
    name="bnpy",
    version="0.2.0",
    install_requires=install_requires,
    extras_require=extras_require,  # 可选依赖支持(网页1)
    python_requires=">=3.7",  # 明确Python版本要求
)