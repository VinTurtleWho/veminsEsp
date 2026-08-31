cmake_minimum_required(VERSION 3.22.1)
project("vemins_engine")

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -ffast-math -flto -fvisibility=hidden -fvisibility-inlines-hidden -Wall -Wextra")

add_library(
    vemins_engine
    SHARED
    memory_reader.cpp
    jni_bridge.cpp
)

target_include_directories(
    vemins_engine
    PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(
    vemins_engine
    PRIVATE
    log
    android
)
