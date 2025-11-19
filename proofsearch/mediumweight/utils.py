# proofsearch/mediumweight/utils.py

import re
import json
import logging
import asyncio
from typing import Dict, List, Set, Tuple, Optional, Any

logger = logging.getLogger(__name__)

class ProofAnalysis:
    """
    Analyzes a Lean proof file to extract declarations, identify errors,
    and construct subproblems for fixing individual proofs.
    """

    def __init__(self, code: str, errors: List[Dict[str, Any]] = None, compilation_scheduler=None):
        """
        Initializes the analysis of the Lean code.

        Args:
            code: The full Lean code as a string.
            errors: A list of error dictionaries from the Lean server (deprecated, for backward compatibility).
            compilation_scheduler: The compilation scheduler for verifying individual lemmas.
        """
        self.code = code
        self._original_code = code  # Keep a copy of the original code
        self.errors = errors if errors is not None else []
        self.lines = self.code.split('\n')
        self.compilation_scheduler = compilation_scheduler
        
        # Store fix history
        self.fix_history = {}  # Maps lemma_name to {'original_subproblem': str, 'fixed_subproblem': str}
        
        # Perform analysis
        self.header = self._extract_header()
        self.declarations = self._extract_declarations()
        
        # Store compilation results for each lemma
        self.lemma_compilation_results = {}  # Maps lemma_name to compilation_result dict
        
        # Error declarations will be populated by async verification
        self.error_declarations = set()
        
        # Mark that verification hasn't been done yet
        self._verification_done = False

    async def verify_all_lemmas(self):
        """
        Asynchronously verifies all lemmas in the code.
        This should be called after initialization.
        """
        if self._verification_done:
            logger.warning("Lemmas already verified, skipping re-verification.")
            return
        
        if self.compilation_scheduler is None:
            logger.warning("No compilation scheduler provided, cannot verify lemmas.")
            return
        
        # Verify all lemmas concurrently
        verification_tasks = []
        lemma_names = []
        
        for name, info in self.declarations.items():
            if info['type'] in ['lemma', 'theorem'] and info['has_proof']:
                lemma_names.append(name)
                verification_tasks.append(self._verify_lemma_async(name))
        
        if verification_tasks:
            results = await asyncio.gather(*verification_tasks, return_exceptions=True)
            
            for name, result in zip(lemma_names, results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to verify lemma '{name}': {result}")
                    self.error_declarations.add(name)
                    self.declarations[name]['is_verified'] = False
                else:
                    self.declarations[name]['is_verified'] = result
                    if not result:
                        self.error_declarations.add(name)
        
        self._verification_done = True
        
        # Cache subproblems after verification is done
        self._cache_subproblems()

    def get_error_lemmas_sorted(self) -> List[str]:
        """
        Returns a sorted list of error lemmas with detailed logging and visualization.
        This method provides comprehensive information about all lemmas/theorems.
        """
        if not self._verification_done:
            logger.warning("Verification not done yet. Call verify_all_lemmas() first.")
            return []
        
        # Collect all lemmas/theorems with their status
        lemma_info = []
        for name, info in self.declarations.items():
            if info['type'] in ['lemma', 'theorem']:
                is_correct = name not in self.error_declarations
                lemma_info.append({
                    'name': name,
                    'type': info['type'],
                    'is_correct': is_correct,
                    'dependencies': info['dependencies'],
                    'has_proof': info['has_proof'],
                    'was_fixed': info.get('was_fixed', False),
                    'compilation_result': self.lemma_compilation_results.get(name, {})
                })
        
        # Sort by declaration order
        lemma_info.sort(key=lambda x: self.declarations[x['name']]['start_line'])
        
        # Log detailed information
        logger.info("=" * 80)
        logger.info("LEMMA/THEOREM VERIFICATION SUMMARY")
        logger.info("=" * 80)
        
        total_lemmas = len(lemma_info)
        correct_lemmas = sum(1 for l in lemma_info if l['is_correct'])
        error_lemmas = total_lemmas - correct_lemmas
        
        logger.info(f"Total lemmas/theorems: {total_lemmas}")
        logger.info(f"✓ Correct: {correct_lemmas}")
        logger.info(f"✗ Errors: {error_lemmas}")
        
        if error_lemmas > 0:
            logger.info("-" * 80)
            logger.info("DETAILED LEMMA STATUS:")
            logger.info("-" * 80)
        
        for info in lemma_info:
            status_symbol = "✓" if info['is_correct'] else "✗"
            fixed_marker = " [FIXED]" if info['was_fixed'] else ""
            
            logger.info(f"{status_symbol} {info['type'].upper()}: {info['name']}{fixed_marker}")
            
            # Show dependencies
            if info['dependencies']:
                dep_status = []
                for dep in sorted(info['dependencies']):
                    if dep in self.declarations:
                        dep_info = self.declarations[dep]
                        if dep_info['type'] in ['lemma', 'theorem']:
                            dep_correct = dep not in self.error_declarations
                            dep_symbol = "✓" if dep_correct else "✗"
                            dep_status.append(f"{dep_symbol} {dep}")
                        else:
                            dep_status.append(f"  {dep} ({dep_info['type']})")
                    else:
                        dep_status.append(f"  {dep}")
                
                logger.info(f"  Dependencies: {', '.join(dep_status)}")
            else:
                logger.info("  Dependencies: None")
            
            # Show compilation result if available
            if info['compilation_result']:
                comp_result = info['compilation_result']
                if comp_result.get('complete'):
                    logger.info("  Compilation: ✓ PASS")
                else:
                    logger.info("  Compilation: ✗ FAIL")
                    if comp_result.get('errors'):
                        error_count = len(comp_result['errors'])
                        logger.info(f"  Error count: {error_count}")
        
        # Draw dependency graph
        self._draw_dependency_graph(lemma_info)
        
        # Return sorted list of error lemmas
        error_list = sorted([info['name'] for info in lemma_info if not info['is_correct']])
        
        if error_list:
            logger.info("=" * 80)
            logger.info(f"ERROR LEMMAS TO FIX ({len(error_list)}):")
            logger.info("=" * 80)
            for i, lemma_name in enumerate(error_list, 1):
                logger.info(f"{i}. {lemma_name}")
        
        return error_list

    def _draw_dependency_graph(self, lemma_info: List[Dict[str, Any]]):
        """
        Draws a simple ASCII dependency graph in the console.
        """
        if not lemma_info:
            return
        
        logger.info("=" * 80)
        logger.info("DEPENDENCY GRAPH")
        logger.info("=" * 80)
        logger.info("Legend: ✓ = Correct, ✗ = Error, → = depends on")
        logger.info("-" * 80)
        
        # Build dependency tree
        for info in lemma_info:
            status_symbol = "✓" if info['is_correct'] else "✗"
            fixed_marker = " [FIXED]" if info['was_fixed'] else ""
            
            logger.info(f"{status_symbol} {info['name']}{fixed_marker}")
            
            if info['dependencies']:
                deps = sorted(info['dependencies'])
                for i, dep in enumerate(deps):
                    is_last = (i == len(deps) - 1)
                    prefix = "└──" if is_last else "├──"
                    
                    if dep in self.declarations:
                        dep_info = self.declarations[dep]
                        if dep_info['type'] in ['lemma', 'theorem']:
                            dep_correct = dep not in self.error_declarations
                            dep_symbol = "✓" if dep_correct else "✗"
                            logger.info(f"    {prefix} {dep_symbol} {dep}")
                        else:
                            logger.info(f"    {prefix}   {dep} ({dep_info['type']})")
                    else:
                        logger.info(f"    {prefix}   {dep} (external)")
        
        logger.info("=" * 80)

    def _extract_header(self) -> str:
        """Extracts the header (imports, opens, set_options) from Lean code."""
        header_lines = []
        for line in self.lines:
            stripped = line.strip()
            if (stripped.startswith('import') or
                stripped.startswith('open') or
                stripped.startswith('set_option') or
                not stripped):
                header_lines.append(line)
            else:
                # Stop at the first line of actual code
                break
        return '\n'.join(header_lines).strip()

    def _extract_declarations(self) -> Dict[str, Dict[str, Any]]:
        """
        Extracts information about all top-level declarations (def, axiom, lemma, theorem).
        """
        declarations = {}
        # This pattern captures the declaration type and its name
        declaration_pattern = r'^\s*(axiom|lemma|theorem|def)\s+([\w\.]+)'
        
        # First pass: Identify all declaration starting lines
        for i, line in enumerate(self.lines):
            match = re.match(declaration_pattern, line)
            if match:
                decl_type, decl_name = match.groups()
                declarations[decl_name] = {
                    'name': decl_name,
                    'type': decl_type,
                    'start_line': i + 1,  # 1-indexed
                    'end_line': i + 1,
                    'dependencies': set(),
                    'has_proof': False,
                    'full_text': '',
                    'original_subproblem': None,  # Will be filled for lemmas/theorems
                    'fixed_subproblem': None,  # Will be filled if fixed
                    'was_fixed': False,
                    'is_verified': False,  # Will be set after compilation verification
                }
        
        # Second pass: Determine end lines, extract full text, and check for proofs
        decl_names = list(declarations.keys())
        sorted_decls = sorted(declarations.values(), key=lambda x: x['start_line'])

        for i, decl_info in enumerate(sorted_decls):
            start_idx = decl_info['start_line'] - 1
            
            # The end is the start of the next declaration or the end of the file
            end_idx = len(self.lines)
            if i + 1 < len(sorted_decls):
                end_idx = sorted_decls[i+1]['start_line'] - 1
            
            decl_info['end_line'] = end_idx
            full_text = '\n'.join(self.lines[start_idx:end_idx]).strip()
            decl_info['full_text'] = full_text
            
            # A lemma/theorem has a proof if it contains ':= by' or ':='
            if decl_info['type'] in ['lemma', 'theorem'] and (':=' in full_text):
                decl_info['has_proof'] = True

        # Third pass: Extract dependencies
        for name, info in declarations.items():
            # Only lemmas and theorems have proofs where we check for dependencies
            if info['type'] in ['lemma', 'theorem', 'def']:
                text_to_check = info['full_text']
                for other_name in decl_names:
                    if other_name != name:
                        # Use word boundaries to avoid matching parts of other names
                        pattern = r'\b' + re.escape(other_name) + r'\b'
                        if re.search(pattern, text_to_check):
                            info['dependencies'].add(other_name)
        
        return declarations

    async def _verify_lemma_async(self, lemma_name: str) -> bool:
        """
        Asynchronously verifies a single lemma by compiling it with its dependencies as axioms.
        The lemma's original proof is kept intact for verification.
        
        Args:
            lemma_name: The name of the lemma to verify
            
        Returns:
            True if the lemma compiles successfully, False otherwise
        """
        if lemma_name not in self.declarations:
            return False
        
        try:
            # Construct the verification code (lemma + dependencies as axioms, WITH original proof)
            verification_code = self._construct_verification_code(lemma_name)
            
            # Compile the verification code
            compilation_info = await self.compilation_scheduler.compile(
                name=f"verify_{lemma_name}",
                code=verification_code
            )
            
            compilation_result = compilation_info.get('compilation_result', {})
            self.lemma_compilation_results[lemma_name] = compilation_result
            
            # Check if compilation was successful
            is_complete = compilation_result.get('complete', False)
            
            logger.info(f"Verification of lemma '{lemma_name}': {'SUCCESS' if is_complete else 'FAILED'}")
            
            if not is_complete:
                logger.debug(f"FAILED CODE:\n\n{verification_code}\n\nErrors: {json.dumps(compilation_result.get('errors', []), indent=2)}")
            
            return is_complete
            
        except Exception as e:
            logger.error(f"Failed to verify lemma '{lemma_name}': {e}", exc_info=True)
            self.lemma_compilation_results[lemma_name] = {
                'complete': False,
                'pass': False,
                'errors': [{'data': f'Verification failed: {e}'}]
            }
            return False

    def _construct_verification_code(self, lemma_name: str) -> str:
        """
        Constructs verification code for a single lemma.
        This includes the lemma with its ORIGINAL PROOF intact, and all dependencies as axioms.
        
        This is different from _construct_subproblem_internal which replaces the proof with sorry.
        """
        if lemma_name not in self.declarations or self.declarations[lemma_name]['type'] not in ['lemma', 'theorem']:
            raise ValueError(f"'{lemma_name}' is not a valid lemma or theorem to verify.")

        target_decl = self.declarations[lemma_name]
        
        # Get dependencies actually used in the proof
        proof_deps = self._get_proof_dependencies(lemma_name)
        
        # Keep the target lemma with its original proof
        target_text = target_decl['full_text']

        context_parts = []
        # Add all context declarations in their original order
        sorted_decls = sorted(self.declarations.values(), key=lambda x: x['start_line'])

        for info in sorted_decls:
            name = info['name']
            decl_type = info['type']
            
            # Skip the target lemma itself
            if name == lemma_name:
                continue

            # Include all definitions
            if decl_type == 'def':
                context_parts.append(info['full_text'])
            # Include axioms only if they are used in the proof
            elif decl_type == 'axiom' and name in proof_deps:
                context_parts.append(info['full_text'])
            # Include correct lemmas/theorems as axioms (only if used)
            elif decl_type in ['lemma', 'theorem'] and name in proof_deps:
                # Check if this dependency is correct
                should_include = False
                
                if name in self.lemma_compilation_results:
                    # Use compilation result
                    should_include = self.lemma_compilation_results[name].get('complete', False)
                elif name not in self.error_declarations:
                    # Not verified yet, assume correct for now
                    should_include = True
                
                if should_include:
                    decl_text = info['full_text']
                    
                    # Convert to axiom format by changing keyword and removing proof
                    if decl_text.startswith('lemma'):
                        axiom_text = decl_text.replace('lemma', 'axiom', 1)
                    else: # theorem
                        axiom_text = decl_text.replace('theorem', 'axiom', 1)
                    
                    if ':=' in axiom_text:
                        axiom_text = axiom_text.split(':=', 1)[0].strip()
                    
                    context_parts.append(axiom_text)

        full_context = '\n\n'.join(context_parts)
        return f"{self.header}\n\n{full_context}\n\n{target_text}"

    def _cache_subproblems(self):
        """Pre-compute and cache subproblems for all lemmas and theorems."""
        for name, info in self.declarations.items():
            if info['type'] in ['lemma', 'theorem']:
                info['original_subproblem'] = self._construct_subproblem_internal(name)

    def _get_proof_dependencies(self, lemma_name: str) -> Set[str]:
        """
        Extracts the actual dependencies used in the proof of a lemma/theorem.
        Only looks at the proof part (after ':= by' or ':=').
        """
        if lemma_name not in self.declarations:
            return set()
        
        target_decl = self.declarations[lemma_name]
        full_text = target_decl['full_text']
        
        # Extract only the proof part
        proof_text = ""
        if ':= by' in full_text:
            proof_text = full_text.split(':= by', 1)[1]
        elif ':=' in full_text:
            proof_text = full_text.split(':=', 1)[1]
        
        # Find all declaration names that appear in the proof
        proof_deps = set()
        for other_name in self.declarations.keys():
            if other_name != lemma_name:
                # Use word boundaries to avoid matching parts of other names
                pattern = r'\b' + re.escape(other_name) + r'\b'
                if re.search(pattern, proof_text):
                    proof_deps.add(other_name)
        
        return proof_deps
    
    def _get_all_dependencies(self, lemma_name: str, visited: Set[str] = None) -> Set[str]:
        """
        Recursively gets all dependencies of a lemma, including transitive dependencies.
        """
        if visited is None:
            visited = set()
        
        if lemma_name not in self.declarations or lemma_name in visited:
            return set()
        
        visited.add(lemma_name)
        all_deps = set()
        
        direct_deps = self.declarations[lemma_name].get('dependencies', set())
        all_deps.update(direct_deps)
        
        for dep in direct_deps:
            if dep in self.declarations and self.declarations[dep]['type'] in ['lemma', 'theorem']:
                indirect_deps = self._get_all_dependencies(dep, visited)
                all_deps.update(indirect_deps)
        
        return all_deps
    
    def is_lemma_fully_correct(self, lemma_name: str) -> bool:
        """
        Checks if a lemma is fully correct by verifying:
        1. The lemma itself compiles successfully (with dependencies as axioms)
        2. All its dependencies are also fully correct
        """
        if lemma_name not in self.declarations:
            return False
        
        # Check if verification has been done
        if not self._verification_done:
            logger.warning(f"Verification not done yet. Call verify_all_lemmas() first.")
            return False
        
        # Check if the lemma has been verified via compilation
        if lemma_name in self.lemma_compilation_results:
            if not self.lemma_compilation_results[lemma_name].get('complete', False):
                return False
        else:
            # If not verified, it's incorrect
            return False
        
        # Check all dependencies are correct
        all_deps = self._get_all_dependencies(lemma_name)
        
        for dep in all_deps:
            if dep in self.declarations and self.declarations[dep]['type'] in ['lemma', 'theorem']:
                # Recursively check if dependency is correct
                if not self.is_lemma_fully_correct(dep):
                    return False
        
        return True
    
    def get_fully_correct_lemmas(self) -> List[Dict[str, Any]]:
        """
        Returns a list of all fully correct lemmas/theorems.
        Uses compilation-based verification.
        """
        if not self._verification_done:
            logger.warning(f"Verification not done yet. Returning empty list.")
            return []
        
        fully_correct = []
        
        for name, info in self.declarations.items():
            if info['type'] in ['lemma', 'theorem'] and info['has_proof']:
                if self.is_lemma_fully_correct(name):
                    fully_correct.append({
                        'name': name,
                        'type': info['type'],
                        'statement': info['full_text'],
                        'dependencies': list(self._get_all_dependencies(name)),
                        'direct_dependencies': list(info['dependencies']),
                        'compilation_result': self.lemma_compilation_results.get(name, {})
                    })
        
        return fully_correct

    def _construct_subproblem_internal(self, lemma_name: str) -> str:
        """
        Internal method to construct a subproblem for a single lemma.
        This version replaces the proof with 'sorry' for the lightweight search to solve.
        Only includes axioms that are actually used in the proof.
        """
        if lemma_name not in self.declarations or self.declarations[lemma_name]['type'] not in ['lemma', 'theorem']:
            raise ValueError(f"'{lemma_name}' is not a valid lemma or theorem to construct a subproblem for.")

        target_decl = self.declarations[lemma_name]
        
        # Get dependencies actually used in the proof
        proof_deps = self._get_proof_dependencies(lemma_name)
        
        # Convert the target lemma to a theorem and remove its proof
        target_text = target_decl['full_text']
        if target_text.startswith('lemma'):
            theorem_text = target_text.replace('lemma', 'theorem', 1)
        else:
            theorem_text = target_text

        # Remove the proof part and replace with sorry
        if ':=' in theorem_text:
            theorem_text = theorem_text.split(':=', 1)[0].strip() + ' := by sorry'
        else: # Should not happen for a valid lemma
            theorem_text += ' := by sorry'

        context_parts = []
        facts = []
        # Add all context declarations in their original order
        sorted_decls = sorted(self.declarations.values(), key=lambda x: x['start_line'])

        for info in sorted_decls:
            name = info['name']
            decl_type = info['type']
            
            # Skip the target lemma itself
            if name == lemma_name:
                continue

            # Include all definitions
            if decl_type == 'def':
                context_parts.append(info['full_text'])
            # Include axioms only if they are used in the proof
            elif decl_type == 'axiom' and name in proof_deps:
                # context_parts.append(info['full_text'])
                facts.append(info['full_text'])
            # Include correct lemmas/theorems as axioms
            elif decl_type in ['lemma', 'theorem'] and name in proof_deps:
                # Check if this dependency is correct
                should_include = False
                
                if name in self.lemma_compilation_results:
                    # Use compilation result
                    should_include = self.lemma_compilation_results[name].get('complete', False)
                elif name not in self.error_declarations:
                    # Not verified yet, assume correct for now
                    should_include = True
                
                if should_include:
                    decl_text = info['full_text']
                    
                    # Convert to axiom format by changing keyword and removing proof
                    if decl_text.startswith('lemma'):
                        axiom_text = decl_text.replace('lemma', 'axiom', 1)
                    else: # theorem
                        axiom_text = decl_text.replace('theorem', 'axiom', 1)
                    
                    if ':=' in axiom_text:
                        axiom_text = axiom_text.split(':=', 1)[0].strip()
                    
                    # context_parts.append(axiom_text)
                    facts.append(axiom_text)

        full_context = '\n\n'.join(context_parts)
        return f"{self.header}\n{full_context}\n{theorem_text}", facts

    def construct_subproblem(self, lemma_name: str) -> str:
        """
        Public method to construct a subproblem for proving a single lemma.
        Returns the cached version if available.
        This subproblem has the proof replaced with 'sorry'.
        """
        if lemma_name in self.declarations and self.declarations[lemma_name].get('original_subproblem'):
            return self.declarations[lemma_name]['original_subproblem']
        return self._construct_subproblem_internal(lemma_name)

    def _generate_unique_name(self, base_name: str, existing_names: Set[str]) -> str:
        """
        Generates a unique name by appending a suffix if the base name conflicts.
        """
        if base_name not in existing_names:
            return base_name
        
        counter = 1
        while f"{base_name}_{counter}" in existing_names:
            counter += 1
        
        return f"{base_name}_{counter}"

    def _rename_declaration_in_text(self, text: str, old_name: str, new_name: str) -> str:
        """
        Renames a declaration in the given text, handling both the declaration itself
        and any references to it.
        """
        # Replace the declaration name (at the start of the declaration)
        declaration_pattern = r'^\s*(axiom|lemma|theorem|def)\s+' + re.escape(old_name) + r'\b'
        text = re.sub(declaration_pattern, r'\1 ' + new_name, text, flags=re.MULTILINE)
        
        # Replace all references to the old name with the new name
        reference_pattern = r'\b' + re.escape(old_name) + r'\b'
        text = re.sub(reference_pattern, new_name, text)
        
        return text

    async def fix_lemma(self, lemma_name: str, fixed_subproblem_code: str):
        """
        Replaces a lemma/theorem in the original code with its fixed version
        and updates the analysis state. Also handles new lemmas introduced in the fix.
        Detects and renames conflicting new lemma names.
        
        The fixed code has already been verified by the lightweight pipeline,
        so we trust that all lemmas (main and helpers) are correct.
        
        Args:
            lemma_name: The name of the lemma to fix
            fixed_subproblem_code: The complete fixed code (already verified by lightweight pipeline)
        """
        if lemma_name not in self.declarations:
            logger.warning(f"Cannot fix '{lemma_name}': not found in original code.")
            return

        # Store the original subproblem before fixing
        original_subproblem, _ = self.declarations[lemma_name].get('original_subproblem')
        if not original_subproblem:
            original_subproblem, _ = self._construct_subproblem_internal(lemma_name)
        
        # Store previously fixed lemmas before re-analysis
        previously_fixed = {name: info for name, info in self.declarations.items() 
                            if info.get('was_fixed', False)}

        # 1. Parse the fixed subproblem to extract all declarations
        fixed_lines = fixed_subproblem_code.split('\n')
        declaration_pattern = r'^\s*(axiom|lemma|theorem|def)\s+([\w\.]+)'
        
        # Find all declarations in the fixed code
        fixed_declarations = {}
        for i, line in enumerate(fixed_lines):
            match = re.match(declaration_pattern, line)
            if match:
                decl_type, decl_name = match.groups()
                fixed_declarations[decl_name] = {
                    'type': decl_type,
                    'start_line': i,
                    'name': decl_name
                }
        
        # Determine end lines for each declaration
        sorted_fixed_decls = sorted(fixed_declarations.values(), key=lambda x: x['start_line'])
        for i, decl_info in enumerate(sorted_fixed_decls):
            start_idx = decl_info['start_line']
            end_idx = len(fixed_lines)
            if i + 1 < len(sorted_fixed_decls):
                end_idx = sorted_fixed_decls[i + 1]['start_line']
            decl_info['end_line'] = end_idx
            decl_info['text'] = '\n'.join(fixed_lines[start_idx:end_idx]).strip()
        
        # 2. Find the target lemma in the fixed code
        if lemma_name not in fixed_declarations:
            logger.warning(f"Could not find declaration for '{lemma_name}' in the provided fixed code.")
            return
        
        target_fixed_decl = fixed_declarations[lemma_name]
        new_decl_text = target_fixed_decl['text']
        
        # 3. Convert back to original type if necessary
        original_info = self.declarations[lemma_name]
        if original_info['type'] == 'lemma' and new_decl_text.startswith('theorem'):
            new_decl_text = new_decl_text.replace('theorem', 'lemma', 1)
        elif original_info['type'] == 'theorem' and new_decl_text.startswith('lemma'):
            new_decl_text = new_decl_text.replace('lemma', 'theorem', 1)
        
        # 4. Identify new lemmas and check for name conflicts
        new_lemmas = []
        name_mappings = {}
        existing_names = set(self.declarations.keys())
        
        for decl_name, decl_info in fixed_declarations.items():
            # Skip axioms and defs as they should already be in context
            if decl_info['type'] in ['axiom', 'def']:
                continue
            # Skip the target lemma itself
            if decl_name == lemma_name:
                continue
            
            # This is a new helper lemma/theorem introduced in the fix
            # Check for name conflict with existing declarations
            if decl_name in existing_names:
                # Generate a unique name
                new_name = self._generate_unique_name(decl_name, existing_names)
                name_mappings[decl_name] = new_name
                existing_names.add(new_name)
                logger.info(f"Renamed conflicting lemma '{decl_name}' to '{new_name}'")
                
                # Update the declaration info
                decl_info['original_name'] = decl_name
                decl_info['name'] = new_name
            else:
                existing_names.add(decl_name)
            
            new_lemmas.append(decl_info)
        
        # Sort new lemmas by their appearance order in fixed code
        new_lemmas.sort(key=lambda x: x['start_line'])
        
        # 5. Apply name mappings to all declarations (if any conflicts were found)
        if name_mappings:
            # Rename in new lemmas
            for lemma_info in new_lemmas:
                for old_name, new_name in name_mappings.items():
                    lemma_info['text'] = self._rename_declaration_in_text(
                        lemma_info['text'], old_name, new_name
                    )
            
            # Rename in the target lemma
            for old_name, new_name in name_mappings.items():
                new_decl_text = self._rename_declaration_in_text(
                    new_decl_text, old_name, new_name
                )
        
        # 6. Build the replacement text
        replacement_parts = []
        
        # Add any new lemmas first (they might be helper lemmas)
        for new_lemma_info in new_lemmas:
            lemma_text = new_lemma_info['text']
            # Ensure proper type (convert theorem to lemma if needed for consistency)
            if lemma_text.startswith('theorem'):
                lemma_text = lemma_text.replace('theorem', 'lemma', 1)
            replacement_parts.append(lemma_text)
        
        # Add the fixed target lemma
        replacement_parts.append(new_decl_text)
        
        replacement_text = '\n\n'.join(replacement_parts)
        
        # 7. Replace in the original code
        start_line_idx = original_info['start_line'] - 1
        end_line_idx = original_info['end_line']
        
        new_lines = self.lines[:start_line_idx]
        new_lines.extend(replacement_text.split('\n'))
        new_lines.extend(self.lines[end_line_idx:])
        
        self.code = '\n'.join(new_lines)
        
        # 8. Store fix history (with renamed code if applicable)
        if name_mappings:
            renamed_fixed_code = fixed_subproblem_code
            for old_name, new_name in name_mappings.items():
                renamed_fixed_code = self._rename_declaration_in_text(
                    renamed_fixed_code, old_name, new_name
                )
            self.fix_history[lemma_name] = {
                'original_subproblem': original_subproblem,
                'fixed_subproblem': renamed_fixed_code,
                'renamings': name_mappings
            }
        else:
            self.fix_history[lemma_name] = {
                'original_subproblem': original_subproblem,
                'fixed_subproblem': fixed_subproblem_code
            }
        
        # 9. Re-run analysis and update state
        self.lines = self.code.split('\n')
        # Store old compilation results
        old_compilation_results = self.lemma_compilation_results.copy()
        
        self.declarations = self._extract_declarations()
        
        # Restore was_fixed status for previously fixed lemmas
        for name in previously_fixed:
            if name in self.declarations:
                self.declarations[name]['was_fixed'] = True
                if name in self.fix_history:
                    self.declarations[name]['fixed_subproblem'] = self.fix_history[name]['fixed_subproblem']
                # Restore compilation results
                if name in old_compilation_results:
                    self.lemma_compilation_results[name] = old_compilation_results[name]
                    self.declarations[name]['is_verified'] = old_compilation_results[name].get('complete', False)
        
        # 10. Mark all fixed lemmas as verified (trust lightweight pipeline result)
        # This includes the main lemma and any new helper lemmas
        lemmas_to_mark_verified = [lemma_name] + [info['name'] for info in new_lemmas]
        
        for verify_name in lemmas_to_mark_verified:
            if verify_name in self.declarations:
                self.declarations[verify_name]['was_fixed'] = True
                self.declarations[verify_name]['is_verified'] = True
                
                # Create a simple success result (no need to actually compile)
                self.lemma_compilation_results[verify_name] = {
                    'complete': True,
                    'pass': True,
                    'errors': [],
                    'verified_by': 'lightweight_pipeline'
                }
                
                # Remove from error declarations if it was there
                if verify_name in self.error_declarations:
                    self.error_declarations.remove(verify_name)
        
        # 11. Mark the main fixed lemma
        if lemma_name in self.declarations:
            self.declarations[lemma_name]['fixed_subproblem'] = self.fix_history[lemma_name]['fixed_subproblem']
        
        # 12. Mark new helper lemmas with additional metadata
        for new_lemma_info in new_lemmas:
            lemma_name_final = new_lemma_info['name']
            if lemma_name_final in self.declarations:
                self.declarations[lemma_name_final]['added_for'] = lemma_name
                if 'original_name' in new_lemma_info:
                    self.declarations[lemma_name_final]['renamed_from'] = new_lemma_info['original_name']

        # Update subproblem cache for new/modified lemmas
        self._cache_subproblems()

        # Log the changes made
        if new_lemmas:
            new_lemma_names = [info['name'] for info in new_lemmas]
            logger.info(f"Added {len(new_lemmas)} new verified helper lemmas while fixing '{lemma_name}': {', '.join(new_lemma_names)}")
        if name_mappings:
            logger.info(f"Applied renamings: {name_mappings}")
        
        logger.info(f"Successfully fixed lemma '{lemma_name}' (verified by lightweight pipeline)")

    def report_json(self) -> Dict[str, Any]:
        """
        Generates a JSON report containing complete analysis information.
        """
        # Prepare declarations data
        declarations_data = {}
        for name, info in self.declarations.items():
            decl_data = {
                'name': name,
                'type': info['type'],
                'start_line': info['start_line'],
                'end_line': info['end_line'],
                'has_proof': info['has_proof'],
                'dependencies': list(info['dependencies']),
                'is_correct': name not in self.error_declarations if info['type'] in ['lemma', 'theorem'] else None,
                'is_verified': info.get('is_verified', False),
                'was_fixed': info.get('was_fixed', False)
            }
            
            # Add compilation result if available
            if name in self.lemma_compilation_results:
                decl_data['compilation_result'] = self.lemma_compilation_results[name]
            
            # Add additional info for new lemmas added during fixes
            if info.get('added_for'):
                decl_data['added_for'] = info['added_for']
            
            # Add renaming info if applicable
            if info.get('renamed_from'):
                decl_data['renamed_from'] = info['renamed_from']
            
            # Add fix history if the declaration was fixed
            if name in self.fix_history:
                decl_data['was_fixed'] = True
                decl_data['fix_history'] = self.fix_history[name]
            
            declarations_data[name] = decl_data
        
        # Build the complete JSON report
        report = {
            'is_proof_correct': self.is_proof_correct(),
            'current_code': self.code,
            'original_code': self._original_code,
            'declarations': declarations_data,
            'error_declarations': list(self.error_declarations),
            'header': self.header,
            'fix_summary': {
                'total_fixes': len(self.fix_history),
                'fixed_lemmas': list(self.fix_history.keys())
            },
            'verification_summary': {
                'total_verified': len(self.lemma_compilation_results),
                'verified_correct': len([r for r in self.lemma_compilation_results.values() if r.get('complete', False)]),
                'verified_incorrect': len([r for r in self.lemma_compilation_results.values() if not r.get('complete', False)])
            }
        }
        
        return report

    def report(self) -> str:
        """Generates a full analysis report of the proof."""
        report_parts = []
        report_parts.append("=" * 50)
        report_parts.append("Lean Proof Analysis Report")
        report_parts.append("=" * 50)
        
        report_parts.append("\n--- Declaration Analysis ---")
        sorted_decls = sorted(self.declarations.values(), key=lambda x: x['start_line'])

        for info in sorted_decls:
            name = info['name']
            decl_type = info['type'].upper()
            status = ""
            if info['type'] in ['lemma', 'theorem']:
                is_error = name in self.error_declarations
                is_verified = info.get('is_verified', False)
                verification_status = ""
                if name in self.lemma_compilation_results:
                    comp_result = self.lemma_compilation_results[name]
                    if comp_result.get('complete'):
                        verification_status = " [Verified: PASS]"
                    else:
                        verification_status = " [Verified: FAIL]"
                elif is_verified:
                    verification_status = " [Verified: PASS]"
                
                status = " (ERROR)" if is_error else " (Correct)"
                status += verification_status
                
                if info.get('was_fixed', False):
                    status += " [FIXED]"
                if info.get('added_for'):
                    status += f" [Added for {info['added_for']}]"
                if info.get('renamed_from'):
                    status += f" [Renamed from {info['renamed_from']}]"
            
            report_parts.append(f"\n{decl_type}: {name}{status}")
            
            deps = info['dependencies']
            if deps:
                report_parts.append(f"  Dependencies: {', '.join(sorted(list(deps)))}")
            else:
                report_parts.append(f"  Dependencies: None")
        
        # Add verification summary
        if self.lemma_compilation_results:
            report_parts.append("\n--- Verification Summary ---")
            total = len(self.lemma_compilation_results)
            passed = len([r for r in self.lemma_compilation_results.values() if r.get('complete', False)])
            failed = total - passed
            report_parts.append(f"Total lemmas verified: {total}")
            report_parts.append(f"Passed: {passed}")
            report_parts.append(f"Failed: {failed}")
        
        # Add fix summary
        if self.fix_history:
            report_parts.append("\n--- Fix Summary ---")
            report_parts.append(f"Total fixes applied: {len(self.fix_history)}")
            report_parts.append(f"Fixed lemmas: {', '.join(self.fix_history.keys())}")

        return '\n'.join(report_parts)

    def is_proof_correct(self) -> bool:
        """
        Checks if there are any remaining declarations with errors.
        Returns True if the proof is fully correct, False otherwise.
        """
        return not self.error_declarations

if __name__ == "__main__":
    # Test case 2
    test_code2 = """
import Mathlib
import Aesop

set_option maxHeartbeats 0

open BigOperators Real Nat Topology Rat

def q_seq_step (m : ℕ) (q_prev : ℚ) : ℚ :=
  ((q_prev.num + m * q_prev.den : ℚ) / (q_prev.den + 1 : ℚ))

axiom squarefree_of_pos (a b : ℕ) (ha : 0 < a) (hb : 0 < b) (hab : a < b) :
  Squarefree (a + b)

lemma Set_Ioi_infinite : Infinite (Set.Ioi (0 : ℕ)) := by
  exact Set.infinite_Ioi

lemma Set_Ioi_pos : ∀ x ∈ Set.Ioi (0 : ℕ), x > 0 := by
  intro x hx
  rcases (Set.mem_Ioi).1 hx with h0
  exact h0

lemma Set_Ioi_squarefree :
    ∀ a ∈ Set.Ioi (0 : ℕ), ∀ b ∈ Set.Ioi (0 : ℕ), a < b → Squarefree (a + b) := by
  intro a ha b hb hab
  have ha_pos : 0 < a := by
    rcases (Set.mem_Ioi).1 ha with h0
    exact h0
  have hb_pos : 0 < b := by
    rcases (Set.mem_Ioi).1 hb with h0
    exact h0

  exact squarefree_of_pos a b ha_pos hb_pos hab

theorem omni_math_problem_73 : ∃ M : Set ℕ, Infinite M ∧ (∀ x ∈ M, x > 0) ∧ (∀ a ∈ M, ∀ b ∈ M, a < b → Squarefree (a + b)) := by
  refine' ⟨Set.Ioi (0 : ℕ), ?_, ?_, ?_⟩
  simp
  · exact Set_Ioi_infinite
  · intro x hx
    exact Set_Ioi_pos x hx
  · intro a ha b hb hab
    exact Set_Ioi_squarefree a ha b hb hab
"""
    test_errors2 = [{'severity': 'error', 'pos': {'line': 16, 'column': 8}, 'endPos': {'line': 16, 'column': 24}, 'data': "unknown constant 'Set.infinite_Ioi'"}, {'severity': 'error', 'pos': {'line': 38, 'column': 2}, 'endPos': {'line': 38, 'column': 6}, 'data': 'simp made no progress'}]

    print("\n\n--- Running Test Case 2: Initial Analysis (Without Compilation Scheduler) ---")
    analysis2 = ProofAnalysis(test_code2, test_errors2, compilation_scheduler=None)
    print(analysis2.report())
    print(f"\nIs proof correct before fixes? {analysis2.is_proof_correct()}")
    
    print("\n\n--- Subproblem for 'omni_math_problem_73' (proof replaced with sorry) ---")
    print(analysis2.construct_subproblem('omni_math_problem_73'))
    
    print("\n\n--- Verification code for 'Set_Ioi_pos' (proof kept intact) ---")
    print(analysis2._construct_verification_code('Set_Ioi_pos'))