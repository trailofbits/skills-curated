# Vulnerability Cheatsheet

Quick-reference for identifying smart contract vulnerabilities during codebase scanning. Each section points to its full reference file for detailed analysis.

---

## Arbitrary Storage Location

**Reference:** `arbitrary-storage-location.md`

User-controlled index on a dynamic array write (or `sstore` with user-controlled slot) allows overwriting any storage slot, including `owner`. The attacker computes an index that maps through the array's keccak256 layout to target critical slots.

```solidity
data[index] = value; // index from user input, no bounds check
```

### Grep-able keywords
`sstore`, `.length =`, `data[`, `array[`

---

## Asserting Contract from Code Size

**Reference:** `asserting-contract-from-code-size.md`

Using `extcodesize` or `.code.length == 0` to check if the caller is an EOA is bypassable -- contracts calling from their constructor have a code size of 0.

```solidity
require(msg.sender.code.length == 0, "no contracts");
```

### Grep-able keywords
`extcodesize`, `.code.length`, `isContract`

---

## Authorization Through tx.origin

**Reference:** `authorization-txorigin.md`

Using `tx.origin` for authorization allows phishing attacks: if the owner calls a malicious contract, that contract can call back into the victim contract and `tx.origin` will still be the owner. Use `msg.sender` instead.

```solidity
require(tx.origin == owner, "not owner");
```

### Grep-able keywords
`tx.origin`

---

## Delegatecall to Untrusted Callee

**Reference:** `delegatecall-untrusted-callee.md`

If the target of a `delegatecall` is user-controlled or set by an unprotected function, an attacker can execute arbitrary code in the context of the calling contract's storage, overwriting critical state like `owner`.

```solidity
(bool success,) = callee.delegatecall(data); // callee from user input
```

### Grep-able keywords
`delegatecall`, `setImplementation`, `upgradeTo`

---

## DoS with Block Gas Limit

**Reference:** `dos-gas-limit.md`

Iterating over an unbounded dynamic array in a single transaction will eventually exceed the block gas limit as the array grows, permanently bricking the function. Replace push-payment with pull-payment or add batching/pagination.

```solidity
for (uint256 i = 0; i < recipients.length; i++) {
    payable(recipients[i]).transfer(reward);
}
```

### Grep-able keywords
`for (`, `while (`, `.length`, `.push(`

---

## DoS with (Unexpected) Revert

**Reference:** `dos-revert.md`

A single reverting external call inside a loop blocks the entire function. Also: strict balance equality checks (`address(this).balance ==`) can be broken by force-sent ETH via `selfdestruct`, and unvalidated division denominators cause revert.

```solidity
require(payable(recipients[i]).send(amounts[i]), "transfer failed"); // in loop
require(address(this).balance == expectedBalance); // broken by selfdestruct
```

### Grep-able keywords
`selfdestruct`, `.balance ==`, `.send(`, `.transfer(`, `require(success`

---

## Hash Collision with abi.encodePacked

**Reference:** `hash-collision.md`

When `abi.encodePacked` has two or more adjacent variable-length arguments (string, bytes, dynamic arrays), bytes can shift between arguments to produce the same encoding: `encodePacked("a","bc") == encodePacked("ab","c")`. Use `abi.encode` instead.

```solidity
keccak256(abi.encodePacked(stringA, stringB)); // collision possible
```

### Grep-able keywords
`abi.encodePacked`

---

## Inadherence to Standards

**Reference:** `inadherence-to-standards.md`

Token implementations may deviate from ERC20/ERC721 specs (missing return values, missing events). Token integrations that use raw `IERC20.transfer()` instead of `SafeERC20` break on non-compliant tokens (USDT). Hardcoding 18 decimals or ignoring fee-on-transfer is also a risk.

```solidity
require(token.transfer(to, amount)); // reverts on USDT (no return value)
```

### Grep-able keywords
`SafeERC20`, `safeTransfer`, `safeTransferFrom`, `.transfer(`, `.transferFrom(`, `.approve(`, `decimals`

---

## Incorrect Constructor Name

**Reference:** `incorrect-constructor.md`

In Solidity <0.4.22, constructors are named functions matching the contract name. A typo or case mismatch (e.g., `owned()` vs `Owned`) makes the constructor a regular public function anyone can call to seize ownership.

```solidity
contract Owned {
    function owned() public { owner = msg.sender; } // case mismatch!
}
```

### Grep-able keywords
`pragma solidity 0.4`, `function Wallet`, `function owned`

---

## Insufficient Access Control

**Reference:** `insufficient-access-control.md`

State-changing functions (ownership transfer, fee setting, minting, pausing) that lack access control modifiers or `require(msg.sender == ...)` checks are callable by anyone. Also check that `initialize()` in upgradeable contracts has the `initializer` modifier.

```solidity
function setOwner(address newOwner) external { owner = newOwner; } // no auth
```

### Grep-able keywords
`onlyOwner`, `onlyRole`, `msg.sender ==`, `initialize(`, `initializer`

---

## Insufficient Gas Griefing

**Reference:** `insufficient-gas-griefing.md`

In meta-transaction/relayer patterns, if replay protection (nonce marking) occurs before the sub-call and the relayer controls forwarded gas, the relayer can provide insufficient gas to silently fail the inner call while permanently consuming the nonce, censoring the action.

```solidity
executed[nonce] = true; // marked before sub-call
(bool success,) = target.call{gas: gasLimit}(data); // may silently fail
```

### Grep-able keywords
`gasleft()`, `.call{gas:`, `executed[`, `nonce`, `meta-transaction`, `relayer`

---

## Lack of Precision

**Reference:** `lack-of-precision.md`

Division before multiplication truncates intermediate results and compounds rounding error. If the numerator is smaller than the denominator, the result truncates to zero. Always multiply first, then divide.

```solidity
uint256 dailyRate = amount / 365;       // truncates
uint256 fee = dailyRate * daysEarly;     // wrong -- should be amount * daysEarly / 365
```

### Grep-able keywords
`/ `, `* `, `WAD`, `RAY`, `1e18`, `mulDiv`

---

## Missing Protection Against Signature Replay

**Reference:** `missing-protection-signature-replay.md`

If a signed message hash does not include a nonce, `address(this)`, and `block.chainid`, signatures can be replayed on the same contract, across contracts, or across chains. Use EIP-712 with a domain separator.

```solidity
bytes32 hash = keccak256(abi.encodePacked(to, amount)); // no nonce, no address, no chainid
```

### Grep-able keywords
`ecrecover`, `ECDSA.recover`, `nonces`, `block.chainid`, `address(this)`, `EIP712`, `domainSeparator`

---

## msg.value Reuse in Loops

**Reference:** `msgvalue-loop.md`

`msg.value` is constant for the entire transaction. Using it inside a loop allows a single payment to pass a `require(msg.value >= price)` check on every iteration, letting the caller buy N items for the price of one.

```solidity
for (uint256 i = 0; i < ids.length; i++) {
    require(msg.value >= price); // passes every iteration with one payment
    _mint(msg.sender, ids[i]);
}
```

### Grep-able keywords
`msg.value`, `multicall`, `delegatecall`

---

## Off-By-One Errors

**Reference:** `off-by-one.md`

Incorrect loop boundaries (`< length - 1` skips last element, `<= length` goes out of bounds) and wrong comparison operators at thresholds (`<` vs `<=`) cause elements to be skipped, out-of-bounds access, or incorrect boundary enforcement.

```solidity
for (uint256 i = 0; i < users.length - 1; i++) // skips last user
```

### Grep-able keywords
`length - 1`, `<= length`, `< length`

---

## Outdated Compiler Version

**Reference:** `outdated-compiler-version.md`

Using an old Solidity version misses critical security features (e.g., <0.8.0 has no built-in overflow checks) and may contain known compiler bugs. Check `pragma solidity` against the latest stable release and the known bugs list.

### Grep-able keywords
`pragma solidity`

---

## Integer Overflow and Underflow

**Reference:** `overflow-underflow.md`

In Solidity <0.8.0, arithmetic wraps silently. In >=0.8.0, arithmetic inside `unchecked {}` or `assembly {}` blocks still wraps. Type downcasts (e.g., `uint8(bigValue)`) silently truncate in all versions.

```solidity
unchecked { x += 1; }       // wraps to 0 at max
uint8 small = uint8(256);   // truncates to 0
```

### Grep-able keywords
`unchecked`, `SafeMath`, `SafeCast`, `uint8(`, `uint16(`, `int8(`, `assembly`

---

## Reentrancy

**Reference:** `reentrancy.md`

If a contract makes an external call (`.call()`, `.send()`, `.transfer()`, `_safeMint()`, ERC777/ERC1155 hooks) before updating state, the callee can re-enter and exploit stale state. Follow checks-effects-interactions or use `nonReentrant`.

```solidity
(bool success,) = msg.sender.call{value: bal}("");  // external call
balances[msg.sender] = 0;                           // state update AFTER -- vulnerable
```

### Grep-able keywords
`.call{value`, `.send(`, `.transfer(`, `_safeMint`, `_safeTransfer`, `onERC721Received`, `onERC1155Received`, `tokensReceived`, `nonReentrant`, `ReentrancyGuard`

---

## Requirement Violation

**Reference:** `requirement-violation.md`

`require()` conditions that use `>` instead of `>=` (or vice versa) reject valid inputs or accept invalid ones. Also, `require` on external call return values may break on non-compliant tokens (e.g., USDT returns no bool).

```solidity
require(balances[msg.sender] > amount); // should be >= to allow exact balance
```

### Grep-able keywords
`require(`, `assert(`

---

## Shadowing State Variables

**Reference:** `shadowing-state-variables.md`

In Solidity <0.6.0, a child contract can re-declare a state variable with the same name as a parent's, creating two separate storage slots. Parent functions read the parent's variable while child functions read the child's, causing inconsistent behavior.

```solidity
contract Child is Base {
    address public owner; // shadows Base.owner -- two different variables
}
```

### Grep-able keywords
`is `, `override`, `virtual`

---

## Timestamp Dependence

**Reference:** `timestamp-dependence.md`

`block.timestamp` can be manipulated by validators within ~15 seconds. Using it for randomness is always exploitable. Using it in tight conditional windows (<=15s) allows validators to include/exclude transactions. Safe for large time windows (hours/days).

```solidity
uint256 result = uint256(keccak256(abi.encodePacked(block.timestamp))) % 6;
```

### Grep-able keywords
`block.timestamp`, `now`, `block.number`

---

## Transaction-Ordering Dependence (Frontrunning)

**Reference:** `transaction-ordering-dependence.md`

Functions whose outcome depends on transaction ordering (swaps without slippage protection, on-chain secret submissions, ERC20 approve race conditions) are vulnerable to frontrunning/sandwiching from mempool observers.

```solidity
function swap(address tokenIn, address tokenOut, uint256 amountIn) external {
    // no minAmountOut -- sandwich attack possible
}
```

### Grep-able keywords
`minAmountOut`, `deadline`, `slippage`, `approve(`, `increaseAllowance`, `commit`, `reveal`

---

## Unchecked Return Values

**Reference:** `unchecked-return-values.md`

Low-level calls (`.call()`, `.send()`, `.delegatecall()`) return a boolean but do not revert on failure. If the return value is not checked, execution continues with state updates that assume success.

```solidity
msg.sender.send(amount);     // return value ignored -- silent failure
totalPaid += amount;          // updated even if send failed
```

### Grep-able keywords
`.call(`, `.send(`, `.delegatecall(`, `require(success`

---

## Unencrypted Private Data On-Chain

**Reference:** `unencrypted-private-data-on-chain.md`

The `private` visibility modifier only prevents other contracts from reading the variable. Anyone can read any storage slot via `eth_getStorageAt`. Never store plaintext secrets, passwords, or keys on-chain.

```solidity
bytes32 private secretAnswer; // readable via eth_getStorageAt
```

### Grep-able keywords
`private`, `secret`, `password`, `key`, `answer`

---

## Unexpected ecrecover Null Address

**Reference:** `unexpected-ecrecover-null-address.md`

`ecrecover` returns `address(0)` for invalid signatures. If the recovered address is not checked against `address(0)` and the expected signer is uninitialized (defaults to `address(0)`), the auth check passes for anyone. Use OpenZeppelin's `ECDSA.recover`.

```solidity
address recovered = ecrecover(hash, v, r, s);
require(recovered == signer); // if signer is address(0), any invalid sig passes
```

### Grep-able keywords
`ecrecover`, `address(0)`, `ECDSA.recover`

---

## Uninitialized Storage Pointer

**Reference:** `uninitialized-storage-pointer.md`

In Solidity <0.5.0, local struct/array variables without an explicit `memory` or `storage` keyword default to `storage` at slot 0, silently overwriting early state variables (e.g., `owner`) on assignment.

```solidity
User u;           // defaults to storage slot 0 in <0.5.0
u.addr = _addr;   // overwrites slot 0 (e.g., owner)
```

### Grep-able keywords
`pragma solidity 0.4`, `storage`, `memory`

---

## Unsupported Opcodes

**Reference:** `unsupported-opcodes.md`

Contracts compiled with Solidity >=0.8.20 emit the `PUSH0` opcode, which is unsupported on some chains. `.transfer()` and `.send()` use a 2300 gas stipend that is insufficient on chains like zkSync Era. Dynamic `create`/`create2` with runtime bytecode fails on zkSync.

```solidity
payable(msg.sender).transfer(amount); // 2300 gas -- fails on zkSync Era
```

### Grep-able keywords
`pragma solidity 0.8.20`, `.transfer(`, `.send(`, `PUSH0`, `selfdestruct`, `create(`, `create2(`

---

## Use of Deprecated Functions

**Reference:** `use-of-deprecated-functions.md`

Deprecated Solidity keywords (`suicide`, `sha3`, `block.blockhash`, `callcode`, `throw`, `msg.gas`, `constant` as function modifier, `var`) may behave unexpectedly or fail to compile on newer versions. `selfdestruct` is also deprecated post-Dencun.

### Grep-able keywords
`suicide`, `sha3`, `block.blockhash`, `callcode`, `throw`, `msg.gas`, `selfdestruct`, `constant`, `var `

---

## Weak Sources of Randomness

**Reference:** `weak-sources-randomness.md`

Randomness derived from on-chain data (`block.timestamp`, `block.prevrandao`, `blockhash`, `block.number`) is deterministic and publicly visible. Another contract in the same transaction can compute the identical "random" value and only call when the outcome is favorable. Use Chainlink VRF.

```solidity
uint256 random = uint256(keccak256(abi.encodePacked(block.timestamp, block.prevrandao))) % 100;
```

### Grep-able keywords
`block.prevrandao`, `block.difficulty`, `blockhash`, `block.timestamp`, `keccak256`, `% `

---

## Assert Violation

**Reference:** `assert-violation.md`

`assert()` should only be used for invariants that can never fail in a correct contract. Using it for input validation or external call checks wastes all remaining gas on failure (<0.8.0) and provides no custom error message. Use `require()` instead.

```solidity
assert(balances[msg.sender] >= amount); // wrong -- should be require
```

### Grep-able keywords
`assert(`

---

## Incorrect Inheritance Order

**Reference:** `incorrect-inheritance-order.md`

Solidity's C3 linearization gives precedence to the rightmost parent in the inheritance list. If two parents define the same function, the wrong order silently resolves to the unintended parent's implementation. Order from most base (left) to most derived (right).

```solidity
contract Treasury is Governance, Ownable { } // Ownable.owner() wins (rightmost)
```

### Grep-able keywords
`is `, `override(`, `virtual`, `super.`

---

## Unsecure Signatures (Composite)

**Reference:** `unsecure-signatures.md`

A composite vulnerability covering all signature anti-patterns: missing replay protection (no nonce/chainId/address), signature malleability (tracking by raw bytes), unchecked ecrecover null address, hash collisions from `abi.encodePacked` with dynamic types, and absence of EIP-712 structured signing.

```solidity
bytes32 hash = keccak256(abi.encodePacked(to, amount)); // no nonce, no chainid
address recovered = ecrecover(hash, v, r, s);            // no null check
require(!used[sig]); used[sig] = true;                    // malleable bypass
```

### Grep-able keywords
`ecrecover`, `ECDSA.recover`, `abi.encodePacked`, `used[sig]`, `EIP712`, `domainSeparator`

---

## Unbounded Return Data

**Reference:** `unbounded-return-data.md`

When `.call()` targets an untrusted address, Solidity automatically copies all return data into memory. A malicious callee can return megabytes of data, causing quadratic memory expansion costs and an out-of-gas revert. Use assembly to bound `returndatacopy`.

```solidity
(bool success,) = callback.call(data); // attacker returns huge data, OOG
```

### Grep-able keywords
`returndatasize`, `returndatacopy`, `ExcessivelySafeCall`, `.call(`

---

## Unused Variables

**Reference:** `unused-variables.md`

Unused state variables, parameters, or discarded return values may indicate dead code or missing logic (e.g., an unchecked transfer return value). Each unused variable should be evaluated: is it safe to remove, or does it signal a bug?

### Grep-able keywords
Compiler warnings; no single keyword -- review declarations vs. references.

---

## Signature Malleability

**Reference:** `signature-malleability.md`

For every ECDSA signature `(r, s, v)`, a complementary signature `(r, n-s, flipped_v)` also recovers to the same address. If deduplication is done by raw signature bytes (`mapping(bytes => bool)`), an attacker can submit the malleable variant to bypass replay protection. Use OpenZeppelin's ECDSA library or track by nonce/hash.

```solidity
mapping(bytes => bool) public usedSignatures; // malleable bypass
```

### Grep-able keywords
`mapping(bytes =>`, `usedSignatures`, `ecrecover`, `ECDSA.recover`

---

## Unsafe Low-Level Call

**Reference:** `unsafe-low-level-call.md`

Low-level `.call()` to an address with no deployed code silently succeeds (the EVM treats it as a successful no-op). Unchecked return values compound the issue. Verify target has code (`target.code.length > 0`) and always check the return boolean.

```solidity
(bool success,) = target.call(data); // succeeds even if target has no code
require(success);                     // passes -- no actual execution occurred
```

### Grep-able keywords
`.call(`, `.delegatecall(`, `.staticcall(`, `.code.length`, `require(success`
