// Copyright 2009-2017 Sandia Corporation. Under the terms
// of Contract DE-NA0003525 with Sandia Corporation, the U.S.
// Government retains certain rights in this software.
//
// Copyright (c) 2009-2017, Sandia Corporation
// All rights reserved.
//
// Portions are copyright of other developers:
// See the file CONTRIBUTORS.TXT in the top level directory
// the distribution for more information.
//
// This file is part of the SST software package. For license
// information, see the LICENSE file in the top level directory of the
// distribution.


#include <sst_config.h>
#include <sst/core/params.h>
#include <sst/core/rng/marsaglia.h>
#include <sst/elements/miranda/generators/randomgen.h>

using namespace SST::Miranda;

RandomGenerator::RandomGenerator( Component* owner, Params& params ) :
	RequestGenerator(owner, params) {

	const uint32_t verbose = params.find<uint32_t>("verbose", 0);

	out = new Output("RandomGenerator[@p:@l]: ", verbose, 0, Output::STDOUT);

	issueCount = params.find<uint64_t>("count", 1000);
	reqLength  = params.find<uint64_t>("length", 8);
	maxAddr    = params.find<uint64_t>("max_address", 524288);

	rng = new MarsagliaRNG(11, 31);

	out->verbose(CALL_INFO, 1, 0, "Will issue %" PRIu64 " operations\n", issueCount);
	out->verbose(CALL_INFO, 1, 0, "Request lengths: %" PRIu64 " bytes\n", reqLength);
	out->verbose(CALL_INFO, 1, 0, "Maximum address: %" PRIu64 "\n", maxAddr);
        write_cmd  = params.find<uint32_t>("write_cmd", 0xFFFF );
        read_cmd   = params.find<uint32_t>("read_cmd", 0xFFFF );

	issueOpFences = params.find<std::string>("issue_op_fences", "yes") == "yes";

        if( write_cmd != 0xFFFF ){
          out->verbose(CALL_INFO, 1, 0, "Custom WR opcode %" PRIu32 "\n", write_cmd );
        }
        if( read_cmd != 0xFFFF ){
          out->verbose(CALL_INFO, 1, 0, "Custom RD opcode %" PRIu32 "\n", read_cmd );
        }
}

RandomGenerator::~RandomGenerator() {
	delete out;
	delete rng;
}

void RandomGenerator::generate(MirandaRequestQueue<GeneratorRequest*>* q) {
	out->verbose(CALL_INFO, 4, 0, "Generating next request number: %" PRIu64 "\n", issueCount);

	const uint64_t rand_addr = rng->generateNextUInt64();
	// Ensure we have a reqLength aligned request
	const uint64_t addr_under_limit = (rand_addr % maxAddr);
	const uint64_t addr = (addr_under_limit < reqLength) ? addr_under_limit :
		(rand_addr % maxAddr) - (rand_addr % reqLength);

	const double op_decide = rng->nextUniform();

	// Populate request
        if( write_cmd == 0xFFFF ){
          // issue standard operation
	  q->push_back(new MemoryOpRequest(addr, reqLength, (op_decide < 0.5) ? READ : WRITE));
        }else{
          // issue custom operation
          MemoryOpRequest *op;
          if( op_decide < 0.5 ){
            op = new MemoryOpRequest( addr, reqLength, read_cmd );
          }else{
            op = new MemoryOpRequest( addr, reqLength, write_cmd );
          }
          q->push_back(op);
        }

	if(issueOpFences) {
		q->push_back(new FenceOpRequest());
	}

	issueCount--;
}

bool RandomGenerator::isFinished() {
	return (issueCount == 0);
}

void RandomGenerator::completed() {

}
