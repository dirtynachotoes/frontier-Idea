cmake_minimum_required(VERSION 3.20)
project(FrontierContract LANGUAGES CXX)
add_executable(frontier_contract contract.cpp)
target_compile_features(frontier_contract PRIVATE cxx_std_17)
