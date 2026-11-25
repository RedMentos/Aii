cmake_minimum_required(VERSION 3.16)
project(v14_native_input_embedding_extractor LANGUAGES C CXX)

set(LLAMA_CPP_DIR "" CACHE PATH "Path to the exact llama.cpp source checkout")
set(V14_LLAMA_REVISION "2851b3bcbf8d993a2243ae751c0a7dfa8e944a40" CACHE STRING "Exact llama.cpp API revision")

if(NOT EXISTS "\${LLAMA_CPP_DIR}/CMakeLists.txt")
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

add_subdirectory("\${LLAMA_CPP_DIR}" "\${CMAKE_BINARY_DIR}/llama.cpp" EXCLUDE_FROM_ALL)

add_executable(native_input_embedding_extractor native_input_embedding_extractor.cpp)
target_compile_features(native_input_embedding_extractor PRIVATE cxx_std_17)
target_include_directories(native_input_embedding_extractor PRIVATE
    "\${LLAMA_CPP_DIR}/src"
    "\${LLAMA_CPP_DIR}/ggml/include"
)
target_compile_definitions(native_input_embedding_extractor PRIVATE
    V14_LLAMA_REVISION="\${V14_LLAMA_REVISION}"
)
target_link_libraries(native_input_embedding_extractor PRIVATE llama)
set_target_properties(native_input_embedding_extractor PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "\${CMAKE_BINARY_DIR}/bin"
)

install(TARGETS native_input_embedding_extractor RUNTIME DESTINATION bin)
