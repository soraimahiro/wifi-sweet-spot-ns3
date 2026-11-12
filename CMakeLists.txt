# Build every cc/*.cc as its own scratch executable (each file has its own
# main(), so they cannot be linked together as the default scratch/<subdir>
# rule would do).
#
# Run, e.g.:
#   ./ns3 run "scratch/wifi-sweet-spot/cc/wifi-central-controlled-aggregation_v199.cc --help"
# or by its short name:
#   ./ns3 run "wifi-central-controlled-aggregation_v199 --help"

file(GLOB sweet_spot_sources CONFIGURE_DEPENDS
     ${CMAKE_CURRENT_SOURCE_DIR}/cc/[^.]*.cc
)

foreach(source_file ${sweet_spot_sources})
  get_filename_component(exec_name ${source_file} NAME_WLE)
  build_exec(
    EXECNAME ${exec_name}
    # must match the output path (scratch/wifi-sweet-spot/cc/): ./ns3 run derives
    # the target name of a scratch program from its path, '/' replaced by '_'
    EXECNAME_PREFIX scratch_wifi-sweet-spot_cc_
    SOURCE_FILES ${source_file}
    LIBRARIES_TO_LINK "${ns3-libs}" "${ns3-contrib-libs}"
    EXECUTABLE_DIRECTORY_PATH ${CMAKE_OUTPUT_DIRECTORY}/scratch/wifi-sweet-spot/cc/
  )
endforeach()
