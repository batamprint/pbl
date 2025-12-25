// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Voting {

    struct Candidate {
        string name;
        uint voteCount;
    }

    Candidate[] private candidates;
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    // ✅ TAMBAH KANDIDAT TANPA DEPLOY ULANG
    function addCandidate(string memory name) public onlyOwner {
        candidates.push(
            Candidate({
                name: name,
                voteCount: 0
            })
        );
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
        require(id < candidates.length, "Invalid candidate");
        return (
            candidates[id].name,
            candidates[id].voteCount
        );
    }

    function candidatesCount() public view returns (uint) {
        return candidates.length;
    }
}
