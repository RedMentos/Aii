cmake_minimum_required(VERSION 3.16)
project(v14_native_latent_receiver LANGUAGES C CXX)

set(LLAMA_CPP_DIR "" CACHE PATH "Path to the pinned llama.cpp source checkout")
set(V14_LLAMA_REVISION "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4" CACHE STRING "Exact llama.cpp source revision")

if(NOT EXISTS "${LLAMA_CPP_DIR}/CMakeLists.txt")
    message(FATAL_ERROR "LLAMA_CPP_DIR must point to the pinned llama.cpp checkout")
endif()

set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_COMMON OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_TOOLS OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_SERVER OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_APP OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_UI OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_MTMD OFF CACHE BOOL "" FORCE)
set(GGML_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(GGML_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)

add_subdirectory("${LLAMA_CPP_DIR}" "${CMAKE_BINARY_DIR}/llama.cpp" EXCLUDE_FROM_ALL)

add_executable(native_latent_receiver native_latent_receiver.cpp)
target_compile_features(native_latent_receiver PRIVATE cxx_std_17)
target_compile_definitions(native_latent_receiver PRIVATE
    V14_WITH_LLAMA=1
    V14_LLAMA_REVISION="${V14_LLAMA_REVISION}"
)
target_link_libraries(native_latent_receiver PRIVATE llama)
set_target_properties(native_latent_receiver PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)

install(TARGETS native_latent_receiver RUNTIME DESTINATION bin)
