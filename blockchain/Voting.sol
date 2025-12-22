// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Voting {

    struct Candidate {
        string name;
        uint voteCount;
    }

    Candidate[] public candidates;

    constructor(string[] memory names) {
        for (uint i = 0; i < names.length; i++) {
            candidates.push(
                Candidate({
                    name: names[i],
                    voteCount: 0
                })
            );
        }
    }

    // ✅ UNLIMITED VOTING
    function vote(uint candidateId) public {
        require(candidateId < candidates.length, "Invalid candidate");
        candidates[candidateId].voteCount++;
    }

    function getCandidate(uint id)
        public
        view
        returns (string memory, uint)
    {
        return (
            candidates[id].name,
            candidates[id].voteCount
        );
    }

    function candidatesCount() public view returns (uint) {
        return candidates.length;
    }
}
