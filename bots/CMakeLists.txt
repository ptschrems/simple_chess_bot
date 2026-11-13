cmake_minimum_required(VERSION 3.20)
project(ChessBots CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Enable maximum optimization (/O2 for MSVC, -O3 for GCC/Clang)
if(MSVC)
    add_compile_options(/O2)
else()
    add_compile_options(-O3)
endif()

# Output all compiled C++ executables directly into bots/
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG "${CMAKE_CURRENT_SOURCE_DIR}")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_CURRENT_SOURCE_DIR}")

# 1. Compile every .cpp file in bots/cppBots/ -> bots/<name>.exe
file(GLOB CPP_BOT_SOURCES CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/cppBots/*.cpp")
foreach(CPP_SRC ${CPP_BOT_SOURCES})
    get_filename_component(BOT_NAME ${CPP_SRC} NAME_WE)
    add_executable(${BOT_NAME} ${CPP_SRC})
    target_include_directories(${BOT_NAME} PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cppBots")
endforeach()

# 2. Compile every .py file in bots/pyBots/ -> bots/<name>.exe via PyInstaller
find_package(Python3 COMPONENTS Interpreter REQUIRED)

file(GLOB PY_BOT_SOURCES CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/pyBots/*.py")
set(PY_BOT_EXES "")

foreach(PY_SRC ${PY_BOT_SOURCES})
    get_filename_component(BOT_NAME ${PY_SRC} NAME_WE)
    set(OUTPUT_EXE "${CMAKE_CURRENT_SOURCE_DIR}/${BOT_NAME}.exe")

    add_custom_command(
        OUTPUT ${OUTPUT_EXE}
        COMMAND ${Python3_EXECUTABLE} -m PyInstaller
            --onefile
            --name ${BOT_NAME}
            --distpath "${CMAKE_CURRENT_SOURCE_DIR}"
            --workpath "${CMAKE_CURRENT_BINARY_DIR}/pyinstaller_${BOT_NAME}"
            --specpath "${CMAKE_CURRENT_BINARY_DIR}/pyinstaller_${BOT_NAME}"
            "${PY_SRC}"
        DEPENDS "${PY_SRC}"
        COMMENT "Building Python bot ${BOT_NAME}.exe..."
        VERBATIM
    )
    list(APPEND PY_BOT_EXES ${OUTPUT_EXE})
endforeach()

add_custom_target(BuildPyBots ALL DEPENDS ${PY_BOT_EXES})