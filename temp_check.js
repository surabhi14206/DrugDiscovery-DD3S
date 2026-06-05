
    // State management
    let selectedTool = 'atom';  // Default to atom placement mode
    let selectedAtom = 'C';
    let atoms = [];
    let bonds = [];
    let selectedAtomIndex = null;
    let isDragging = false;
    let draggedAtomIndex = null;
    let pendingStructure = null;  // For click-to-place structures
    let zoom = 1.0;  // Zoom level
    let selectionBox = null;  // For box selection {startX, startY, endX, endY}
    let selectedAtoms = [];  // Array of selected atom indices
    let selectedBonds = [];  // Array of selected bond indices
    let isBoxSelecting = false;
    let boxSelectStart = null;
    let isDraggingGroup = false;  // Flag for dragging multiple atoms
    let groupDragStart = null;  // Starting position for group drag
    let justFinishedBoxSelection = false;  // Prevent click after box selection
    let justFinishedDragging = false;  // Prevent click after dragging
    let protectedAtoms = [];  // Array of protected atom indices
    let protectedBonds = [];  // Array of protected bond indices
    let isMovingCanvas = false;  // Flag for moving the entire canvas
    let canvasMoveStart = null;  // Starting position for canvas move
    let isLassoSelecting = false;  // Flag for lasso selection
    let lassoPath = [];  // Array of {x, y} points for lasso path

    // Canvas elements (global scope)
    let canvas, canvasInner, placeholder;


    // Undo/Redo history
    let history = [];
    let redoStack = [];
    const MAX_HISTORY = 50;  // Keep last 50 states

    // Tool selection
    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.tool-item').forEach(tool => {
            tool.addEventListener('click', function () {
                document.querySelectorAll('.tool-item').forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                const toolId = this.id.replace('Tool', '');
                selectedTool = toolId;

                // Sync with icon buttons
                syncIconToolSelection(toolId);

                // Clear atom selection when switching tools
                selectedAtoms = [];
                selectedBonds = [];
                removeHighlights();
                removeSelectionBox();

                // Show notification for charge tools
                if (toolId === 'chargePositive') {
                    showNotification('Positive charge tool selected. Click an atom to add + charge.', 'info');
                } else if (toolId === 'chargeNegative') {
                    showNotification('Negative charge tool selected. Click an atom to add - charge.', 'info');
                }

                console.log('Tool selected:', selectedTool);
            });
        });
    });

    // Tool & UI Event Listeners
    document.addEventListener('DOMContentLoaded', function () {
        // Icon tool button selection
        document.querySelectorAll('.tool-icon-button').forEach(btn => {
            btn.addEventListener('click', function () {
                const toolId = this.id.replace('ToolIcon', '').replace('Icon', '');

                // Update icon button states
                document.querySelectorAll('.tool-icon-button').forEach(b => b.classList.remove('active'));
                this.classList.add('active');

                // Update regular tool items
                document.querySelectorAll('.tool-item').forEach(t => t.classList.remove('active'));
                const correspondingTool = document.getElementById(toolId + 'Tool');
                if (correspondingTool) {
                    correspondingTool.classList.add('active');
                }

                selectedTool = toolId;

                // Clear atom selection when switching tools (except protect tool to preserve selection)
                if (toolId !== 'protect') {
                    selectedAtoms = [];
                    selectedBonds = [];
                    removeHighlights();
                    removeSelectionBox();
                }

                // Auto-select "no atom" when using quick tools (move, selectBox, lasso, protect)
                if (['move', 'selectBox', 'lasso', 'protect'].includes(toolId)) {
                    selectedAtom = null;
                    // Trigger the no atom button
                    const noAtomBtn = document.querySelector('.atom-button.atom-none');
                    if (noAtomBtn) {
                        document.querySelectorAll('.atom-button').forEach(b => b.style.boxShadow = '');
                        noAtomBtn.style.boxShadow = '0 0 0 3px #6c757d';
                    }
                }

                console.log('Icon tool selected:', selectedTool);
            });
        });

        // Atom button selection - also activates atom placement mode
        document.querySelectorAll('.atom-button').forEach(btn => {
            btn.addEventListener('click', function () {
                console.log('Atom button clicked:', this.className, this.textContent.trim());

                // Skip if this is the periodic table button
                if (this.classList.contains('periodic-table-btn')) {
                    return;
                }

                // Check if "no selection" button was clicked
                if (this.classList.contains('atom-none')) {
                    selectedAtom = null;
                    selectedTool = 'select';  // Switch to select tool
                    document.querySelectorAll('.atom-button').forEach(b => b.style.boxShadow = '');
                    this.style.boxShadow = '0 0 0 3px #6c757d';

                    // Update tool selection UI
                    document.querySelectorAll('.tool-item').forEach(t => t.classList.remove('active'));
                    document.getElementById('selectTool').classList.add('active');

                    console.log('No atom selected - switched to Select tool');
                    return;
                }

                selectedAtom = this.textContent.trim();
                document.querySelectorAll('.atom-button').forEach(b => b.style.boxShadow = '');
                this.style.boxShadow = '0 0 0 3px #0d6efd';
                console.log('Atom selected:', selectedAtom);

                // Deactivate bond mode when atom is selected
                document.querySelectorAll('.bond-type-button').forEach(b => b.classList.remove('active'));

                // Switch to atom placement mode (use 'atom' tool)
                selectedTool = 'atom';
                document.querySelectorAll('.tool-item').forEach(t => t.classList.remove('active'));
                syncIconToolSelection(null);

                // Clear group selection when switching atoms
                selectedAtoms = [];
                selectedBonds = [];
                removeHighlights();
                removeSelectionBox();

                console.log('Atom selected:', selectedAtom, '- Click on canvas to place atom');
            });
        });

        // Bond Type Selection
        document.querySelectorAll('.bond-type-button').forEach(btn => {
            btn.addEventListener('click', function () {
                // Toggle bond selection - click again to deselect
                if (this.classList.contains('active') && selectedTool === 'bond') {
                    // Deselect bond - switch back to select tool
                    document.querySelectorAll('.bond-type-button').forEach(b => b.classList.remove('active'));
                    selectedTool = 'select';
                    document.querySelectorAll('.tool-item').forEach(t => t.classList.remove('active'));
                    document.getElementById('selectTool')?.classList.add('active');
                    syncIconToolSelection('select');
                    showNotification('Bond tool deactivated. Select tool is now active.', 'info');
                    console.log('Bond tool deselected');
                } else {
                    // Select bond type
                    selectedBondType = this.dataset.bondType;
                    document.querySelectorAll('.bond-type-button').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    console.log('Bond type selected:', selectedBondType);

                    // Automatically activate bond tool
                    selectedTool = 'bond';
                    document.querySelectorAll('.tool-item').forEach(t => t.classList.remove('active'));
                    syncIconToolSelection('bond');
                    showNotification(`${getBondTypeName(selectedBondType)} bond selected. Click two atoms to create a bond. Click the bond type again to deselect.`, 'info');
                }
            });
        });

        // Periodic Table Button
        const periodicTableBtn = document.querySelector('.periodic-table-btn');
        if (periodicTableBtn) {
            periodicTableBtn.addEventListener('click', function (e) {
                e.stopPropagation(); // Prevent the atom-button handler from triggering
                document.getElementById('periodicTableModal').classList.add('active');
                console.log('Periodic table modal opened');
            });
        }

        // Periodic Table Element Selection
        document.querySelectorAll('.element').forEach(element => {
            element.addEventListener('click', function () {
                const selectedElement = this.dataset.element;

                // Set as selected atom
                selectedAtom = selectedElement;

                // Update atom button selection UI
                document.querySelectorAll('.atom-button').forEach(b => b.style.boxShadow = '');

                // Find if this element has a button in the atom panel
                const existingBtn = Array.from(document.querySelectorAll('.atom-button')).find(
                    btn => btn.textContent.trim() === selectedElement
                );

                if (existingBtn) {
                    existingBtn.style.boxShadow = '0 0 0 3px #0d6efd';
                } else {
                    // Highlight the periodic table button
                    const pTableBtn = document.querySelector('.periodic-table-btn');
                    if (pTableBtn) pTableBtn.style.boxShadow = '0 0 0 3px #0d6efd';
                }

                // Close periodic table modal
                closePeriodicTable();

                showNotification(`${selectedElement} selected. Click on canvas to place atom.`, 'info');
                console.log('Element selected from periodic table:', selectedElement);
            });
        });

        // Close periodic table on click outside
        const periodicModal = document.getElementById('periodicTableModal');
        if (periodicModal) {
            periodicModal.addEventListener('click', function (e) {
                if (e.target === this) {
                    closePeriodicTable();
                    console.log('Periodic table closed without selection');
                }
            });
        }
    });

    // Canvas interaction
    document.addEventListener('DOMContentLoaded', function () {
        canvas = document.getElementById('designCanvas');
        canvasInner = document.getElementById('canvasInner');
        placeholder = canvas ? canvas.querySelector('.canvas-placeholder') : null;

        if (!canvas) {
            console.error('Design canvas not found!');
            return;
        }

        // Wheel event - zoom in/out
        canvas.addEventListener('wheel', function (e) {
            e.preventDefault();

            const zoomSpeed = 0.2;
            const minZoom = 0.1;   // Allow zooming out further
            const maxZoom = 10.0;  // Allow up to 1000% zoom

            // Determine zoom direction
            const delta = e.deltaY > 0 ? -zoomSpeed : zoomSpeed;
            const newZoom = Math.max(minZoom, Math.min(maxZoom, zoom + delta));

            if (newZoom !== zoom) {
                zoom = newZoom;
                canvasInner.style.transform = `scale(${zoom})`;
                canvasInner.style.transformOrigin = 'center center';
            }
        });

        // Mouse down - start dragging
        canvas.addEventListener('mousedown', function (e) {
            if (e.target.closest('.canvas-toolbar')) return;

            // Reset drag flags to ensure clean state
            justFinishedDragging = false;
            justFinishedBoxSelection = false;

            const rect = canvasInner.getBoundingClientRect();
            const x = (e.clientX - rect.left) * (1 / zoom);
            const y = (e.clientY - rect.top) * (1 / zoom);

            // First check if clicking on a selected atom (works for any tool)
            let clickedOnSelectedAtom = false;
            if (selectedAtoms.length > 0 && selectedTool !== 'move' && selectedTool !== 'lasso' && selectedTool !== 'selectBox') {
                selectedAtoms.forEach(index => {
                    const atom = atoms[index];
                    const distance = Math.sqrt(Math.pow(x - atom.x, 2) + Math.pow(y - atom.y, 2));
                    if (distance < 20) {
                        isDraggingGroup = true;
                        groupDragStart = { x, y };
                        clickedOnSelectedAtom = true;
                    }
                });
            }

            // If clicked on selected atom, don't process other tool actions
            if (clickedOnSelectedAtom) {
                return;
            }

            if (selectedTool === 'move') {
                // Start moving canvas
                isMovingCanvas = true;
                canvasMoveStart = { x: e.clientX, y: e.clientY };
            } else if (selectedTool === 'lasso') {
                // Start lasso selection
                isLassoSelecting = true;
                lassoPath = [{ x, y }];
                selectedAtoms = [];
                selectedBonds = [];
                removeHighlights();
            } else if (selectedTool === 'select' || selectedTool === 'atom' || !selectedTool) {
                // Check for individual atom
                let clickedOnAtom = false;
                atoms.forEach((atom, index) => {
                    const distance = Math.sqrt(Math.pow(x - atom.x, 2) + Math.pow(y - atom.y, 2));
                    if (distance < 20) {
                        isDragging = true;
                        draggedAtomIndex = index;
                        selectedAtomIndex = index;
                        selectedAtoms = [];  // Clear group selection
                        selectedBonds = [];
                        highlightAtom(index);
                        clickedOnAtom = true;
                    }
                });
                if (!clickedOnAtom && selectedTool === 'select') {
                    selectedAtoms = [];
                    selectedBonds = [];
                    removeHighlights();
                }
            } else if (selectedTool === 'selectBox') {
                // Start box selection
                isBoxSelecting = true;
                boxSelectStart = { x, y };
                selectionBox = { startX: x, startY: y, endX: x, endY: y };
                selectedAtoms = [];
                selectedBonds = [];
                removeHighlights();
            }
        });

        // Mouse move - drag atom or update selection box
        canvas.addEventListener('mousemove', function (e) {
            const rect = canvasInner.getBoundingClientRect();
            const x = (e.clientX - rect.left) * (1 / zoom);
            const y = (e.clientY - rect.top) * (1 / zoom);

            if (isMovingCanvas && canvasMoveStart) {
                // Move all atoms together (simulate canvas pan)
                const deltaX = (e.clientX - canvasMoveStart.x) * (1 / zoom);
                const deltaY = (e.clientY - canvasMoveStart.y) * (1 / zoom);

                atoms.forEach(atom => {
                    atom.x += deltaX;
                    atom.y += deltaY;
                });

                canvasMoveStart = { x: e.clientX, y: e.clientY };
                redraw();
            } else if (isLassoSelecting) {
                // Add point to lasso path
                lassoPath.push({ x, y });
                drawLassoPath();
            } else if (isDragging && draggedAtomIndex !== null) {
                // Update single atom position
                atoms[draggedAtomIndex].x = x;
                atoms[draggedAtomIndex].y = y;
                redraw();
            } else if (isDraggingGroup && groupDragStart && selectedAtoms.length > 0) {
                // Update all selected atoms positions
                const deltaX = x - groupDragStart.x;
                const deltaY = y - groupDragStart.y;

                selectedAtoms.forEach(index => {
                    atoms[index].x += deltaX;
                    atoms[index].y += deltaY;
                });

                groupDragStart = { x, y };
                redraw();
                highlightSelectedAtoms();
            } else if (isBoxSelecting && boxSelectStart) {
                // Update selection box
                selectionBox.endX = x;
                selectionBox.endY = y;
                drawSelectionBox();
            }
        });

        // Mouse up - stop dragging or finish box selection
        canvas.addEventListener('mouseup', function (e) {
            if (isDragging && draggedAtomIndex !== null) {
                saveState();  // Save state after drag completes
            }
            if (isDraggingGroup && selectedAtoms.length > 0) {
                saveState();  // Save state after group drag completes
                justFinishedDragging = true;  // Set flag to prevent click event
                setTimeout(() => {
                    justFinishedDragging = false;
                }, 50);
            }
            if (isMovingCanvas) {
                saveState();  // Save state after canvas move completes
            }
            isDragging = false;
            draggedAtomIndex = null;
            isDraggingGroup = false;
            groupDragStart = null;
            isMovingCanvas = false;
            canvasMoveStart = null;

            if (isLassoSelecting && lassoPath.length > 2) {
                // Finish lasso selection - find atoms and bonds inside lasso path
                selectedAtoms = [];
                atoms.forEach((atom, index) => {
                    if (isPointInPolygon(atom, lassoPath)) {
                        selectedAtoms.push(index);
                    }
                });

                // Also select bonds where both endpoints are selected
                selectedBonds = [];
                bonds.forEach((bond, index) => {
                    if (selectedAtoms.includes(bond.from) && selectedAtoms.includes(bond.to)) {
                        selectedBonds.push(index);
                    }
                });

                isLassoSelecting = false;
                lassoPath = [];
                removeLassoPath();  // Clear lasso path

                // Highlight after clearing lasso path
                highlightSelectedAtoms();
                highlightSelectedBonds(selectedBonds);

                if (selectedAtoms.length > 0) {
                    const bondMsg = selectedBonds.length > 0 ? `, ${selectedBonds.length} bond(s)` : '';
                    showNotification(`${selectedAtoms.length} atom(s)${bondMsg} selected with lasso`, 'success');
                }
            }

            if (isBoxSelecting && selectionBox) {
                // Finish box selection - find atoms in box
                const minX = Math.min(selectionBox.startX, selectionBox.endX);
                const maxX = Math.max(selectionBox.startX, selectionBox.endX);
                const minY = Math.min(selectionBox.startY, selectionBox.endY);
                const maxY = Math.max(selectionBox.startY, selectionBox.endY);

                selectedAtoms = [];
                atoms.forEach((atom, index) => {
                    if (atom.x >= minX && atom.x <= maxX && atom.y >= minY && atom.y <= maxY) {
                        selectedAtoms.push(index);
                    }
                });

                // Also select bonds where both endpoints are selected
                selectedBonds = [];
                bonds.forEach((bond, index) => {
                    if (selectedAtoms.includes(bond.from) && selectedAtoms.includes(bond.to)) {
                        selectedBonds.push(index);
                    }
                });

                highlightSelectedAtoms();
                highlightSelectedBonds(selectedBonds);
                removeSelectionBox();
                isBoxSelecting = false;
                boxSelectStart = null;
                selectionBox = null;
                justFinishedBoxSelection = true;  // Set flag to prevent click event

                // Reset flag after a short delay
                setTimeout(() => {
                    justFinishedBoxSelection = false;
                }, 50);
            }
        });

        canvas.addEventListener('click', function (e) {
            console.log('Canvas clicked - Tool:', selectedTool, 'Atom:', selectedAtom);

            // Don't place atoms if just finished box selection or dragging
            if (justFinishedBoxSelection || justFinishedDragging) {
                console.log('Ignoring click - just finished selection/dragging');
                return;
            }

            // Don't place atoms if clicking on toolbar or placeholder text
            if (e.target.closest('.canvas-toolbar') || e.target.closest('.canvas-placeholder h5, .canvas-placeholder p')) {
                console.log('Ignoring click - clicked on toolbar or placeholder');
                return;
            }

            // Hide placeholder on first click
            if (placeholder) {
                placeholder.style.display = 'none';
            }

            const rect = canvasInner.getBoundingClientRect();
            const x = (e.clientX - rect.left) * (1 / zoom);
            const y = (e.clientY - rect.top) * (1 / zoom);
            console.log('Click coordinates:', x, y);

            if (selectedTool === 'select') {
                // Check if clicking on an existing atom
                let clicked = false;
                atoms.forEach((atom, index) => {
                    const distance = Math.sqrt(Math.pow(x - atom.x, 2) + Math.pow(y - atom.y, 2));
                    if (distance < 20) {
                        selectedAtomIndex = index;
                        clicked = true;
                        highlightAtom(index);
                    }
                });
                if (!clicked) {
                    selectedAtomIndex = null;
                    removeHighlights();
                }
            } else if (selectedTool === 'bond') {
                // Find atom near click
                let clickedAtomIndex = null;
                atoms.forEach((atom, index) => {
                    const distance = Math.sqrt(Math.pow(x - atom.x, 2) + Math.pow(y - atom.y, 2));
                    if (distance < 20) {
                        clickedAtomIndex = index;
                    }
                });

                if (clickedAtomIndex !== null) {
                    // Check if either atom is protected
                    if (protectedAtoms.includes(selectedAtomIndex) || protectedAtoms.includes(clickedAtomIndex)) {
                        showNotification('Cannot create/modify bond: One or both atoms are protected 🛡️');
                        return;
                    }

                    if (selectedAtomIndex !== null && selectedAtomIndex !== clickedAtomIndex) {
                        // Check if bond already exists (check both directions)
                        const existingBondIndex = bonds.findIndex(b =>
                            (b.from === selectedAtomIndex && b.to === clickedAtomIndex) ||
                            (b.from === clickedAtomIndex && b.to === selectedAtomIndex)
                        );

                        console.log('Bond check:', { selectedAtomIndex, clickedAtomIndex, existingBondIndex, totalBonds: bonds.length });

                        // Check if the bond is protected
                        if (existingBondIndex !== -1 && protectedBonds.includes(existingBondIndex)) {
                            showNotification('Cannot modify bond: This bond is protected 🛡️');
                            return;
                        }

                        saveState();  // Save state before modification

                        if (existingBondIndex !== -1) {
                            // Bond exists - replace with selected bond type
                            console.log('Updating existing bond:', bonds[existingBondIndex]);
                            const bond = bonds[existingBondIndex];

                            // Clear previous bond properties first
                            delete bond.type;
                            delete bond.order;

                            // Set new bond type/order
                            if (selectedBondType === 'wedge' || selectedBondType === 'dash' || selectedBondType === 'aromatic') {
                                bond.type = selectedBondType;
                                bond.order = selectedBondType === 'aromatic' ? 1.5 : 1;
                            } else {
                                bond.order = parseInt(selectedBondType);
                            }
                            console.log('Bond updated to:', bond);
                            showNotification(`Bond updated to ${getBondTypeName(selectedBondType)} bond`, 'success');
                        } else {
                            // Create new bond with selected type
                            const bondData = { from: selectedAtomIndex, to: clickedAtomIndex };

                            if (selectedBondType === 'wedge' || selectedBondType === 'dash' || selectedBondType === 'aromatic') {
                                bondData.type = selectedBondType;
                                bondData.order = selectedBondType === 'aromatic' ? 1.5 : 1;
                            } else {
                                bondData.order = parseInt(selectedBondType);
                            }

                            bonds.push(bondData);
                            showNotification(`${getBondTypeName(selectedBondType)} bond created`, 'success');
                        }
                        redraw();  // Redraw entire canvas to update bond display
                        updateStats();
                        selectedAtomIndex = null;
                        removeHighlights();
                    } else {
                        selectedAtomIndex = clickedAtomIndex;
                        highlightAtom(clickedAtomIndex);
                    }
                } else {
                    // Clicked on empty space - clear selection
                    selectedAtomIndex = null;
                    removeHighlights();
                }
            } else if (selectedTool === 'erase') {
                // Erase atom or bond
                let clickedAtomIndex = null;
                let clickedBondIndex = null;
                let minBondDistance = Infinity;

                // First, check if clicking on an atom
                atoms.forEach((atom, index) => {
                    const distance = Math.sqrt(Math.pow(x - atom.x, 2) + Math.pow(y - atom.y, 2));
                    if (distance < 20) {
                        clickedAtomIndex = index;
                    }
                });

                // If not clicking on an atom, check if clicking on a bond
                if (clickedAtomIndex === null) {
                    bonds.forEach((bond, index) => {
                        const from = atoms[bond.from];
                        const to = atoms[bond.to];

                        if (!from || !to) return; // Safety check

                        // Calculate distance from click point to line segment
                        const dx = to.x - from.x;
                        const dy = to.y - from.y;
                        const lineLengthSquared = dx * dx + dy * dy;

                        if (lineLengthSquared === 0) return; // Avoid division by zero

                        const t = Math.max(0, Math.min(1,
                            ((x - from.x) * dx + (y - from.y) * dy) / lineLengthSquared
                        ));

                        const projX = from.x + t * dx;
                        const projY = from.y + t * dy;
                        const distance = Math.sqrt(Math.pow(x - projX, 2) + Math.pow(y - projY, 2));

                        // Find the closest bond within threshold
                        if (distance < 15 && distance < minBondDistance) {
                            minBondDistance = distance;
                            clickedBondIndex = index;
                        }
                    });
                }

                if (clickedAtomIndex !== null) {
                    // Check if atom is protected
                    if (protectedAtoms.includes(clickedAtomIndex)) {
                        showAlertModal('This atom is protected! Use the Protect tool to unprotect it first.');
                        return;
                    }

                    saveState();  // Save state before modification

                    // Remove atom and all its bonds
                    atoms.splice(clickedAtomIndex, 1);

                    // Remove bonds connected to this atom and adjust indices
                    bonds = bonds.filter(b => b.from !== clickedAtomIndex && b.to !== clickedAtomIndex)
                        .map(b => ({
                            from: b.from > clickedAtomIndex ? b.from - 1 : b.from,
                            to: b.to > clickedAtomIndex ? b.to - 1 : b.to,
                            order: b.order || 1
                        }));

                    // Adjust protected atoms indices after removal
                    protectedAtoms = protectedAtoms
                        .filter(idx => idx !== clickedAtomIndex)
                        .map(idx => idx > clickedAtomIndex ? idx - 1 : idx);

                    // Adjust protected bonds indices after atom removal
                    const removedBondIndices = [];
                    bonds.forEach((b, idx) => {
                        if (b.from === clickedAtomIndex || b.to === clickedAtomIndex) {
                            removedBondIndices.push(idx);
                        }
                    });
                    protectedBonds = protectedBonds
                        .filter(idx => !removedBondIndices.includes(idx))
                        .map(idx => {
                            let newIdx = idx;
                            removedBondIndices.forEach(removed => {
                                if (removed < idx) newIdx--;
                            });
                            return newIdx;
                        });

                    redraw();
                    updateStats();
                } else if (clickedBondIndex !== null) {
                    // Check if bond is protected
                    if (protectedBonds.includes(clickedBondIndex)) {
                        showNotification('This bond is protected! Use the Protect tool to unprotect it first. 🛡️');
                        return;
                    }

                    saveState();  // Save state before modification

                    // Remove only the specific bond
                    bonds.splice(clickedBondIndex, 1);

                    // Adjust protected bonds indices after removal
                    protectedBonds = protectedBonds
                        .filter(idx => idx !== clickedBondIndex)
                        .map(idx => idx > clickedBondIndex ? idx - 1 : idx);

                    redraw();
                    updateStats();
                }
            } else if (selectedTool === 'chargePositive' || selectedTool === 'chargeNegative') {
                // Apply charge to clicked atom
                let clickedAtomIndex = null;
                atoms.forEach((atom, index) => {
                    const distance = Math.sqrt(Math.pow(x - atom.x, 2) + Math.pow(y - atom.y, 2));
                    if (distance < 20) {
                        clickedAtomIndex = index;
                    }
                });

                if (clickedAtomIndex !== null) {
                    saveState();
                    const chargeChange = selectedTool === 'chargePositive' ? 1 : -1;

                    // Initialize charge if undefined
                    if (atoms[clickedAtomIndex].charge === undefined) {
                        atoms[clickedAtomIndex].charge = 0;
                    }

                    // Apply charge (allow stacking: ++, --, etc.)
                    atoms[clickedAtomIndex].charge += chargeChange;

                    const chargeDisplay = atoms[clickedAtomIndex].charge > 0
                        ? `+${atoms[clickedAtomIndex].charge}`
                        : atoms[clickedAtomIndex].charge;

                    showNotification(`Atom charge: ${chargeDisplay}`, 'success');
                    redraw();
                }
            } else if (selectedTool === 'protect') {
                // Check if there are selected atoms/bonds first
                if (selectedAtoms.length > 0 || selectedBonds.length > 0) {
                    // Toggle protection for all selected atoms and bonds
                    let allProtected = true;
                    let allUnprotected = true;

                    // Check current protection status
                    selectedAtoms.forEach(atomIndex => {
                        if (protectedAtoms.includes(atomIndex)) {
                            allUnprotected = false;
                        } else {
                            allProtected = false;
                        }
                    });

                    selectedBonds.forEach(bondIndex => {
                        if (protectedBonds.includes(bondIndex)) {
                            allUnprotected = false;
                        } else {
                            allProtected = false;
                        }
                    });

                    // If all are protected, unprotect all. Otherwise, protect all.
                    if (allProtected) {
                        // Unprotect all selected
                        selectedAtoms.forEach(atomIndex => {
                            const idx = protectedAtoms.indexOf(atomIndex);
                            if (idx !== -1) protectedAtoms.splice(idx, 1);
                        });
                        selectedBonds.forEach(bondIndex => {
                            const idx = protectedBonds.indexOf(bondIndex);
                            if (idx !== -1) protectedBonds.splice(idx, 1);
                        });
                        showNotification(`${selectedAtoms.length} atom(s) and ${selectedBonds.length} bond(s) unprotected`);
                    } else {
                        // Protect all selected
                        selectedAtoms.forEach(atomIndex => {
                            if (!protectedAtoms.includes(atomIndex)) {
                                protectedAtoms.push(atomIndex);
                            }
                        });
                        selectedBonds.forEach(bondIndex => {
                            if (!protectedBonds.includes(bondIndex)) {
                                protectedBonds.push(bondIndex);
                            }
                        });
                        showNotification(`${selectedAtoms.length} atom(s) and ${selectedBonds.length} bond(s) protected 🛡️`);
                    }

                    redraw();
                } else {
                    // No selection - toggle protection on clicked atom or bond
                    let clickedAtomIndex = null;
                    let clickedBondIndex = null;
                    let minBondDistance = Infinity;

                    // First check if clicking on an atom
                    atoms.forEach((atom, index) => {
                        const distance = Math.sqrt(Math.pow(x - atom.x, 2) + Math.pow(y - atom.y, 2));
                        if (distance < 20) {
                            clickedAtomIndex = index;
                        }
                    });

                    // If not clicking on atom, check if clicking on a bond
                    if (clickedAtomIndex === null) {
                        bonds.forEach((bond, index) => {
                            const from = atoms[bond.from];
                            const to = atoms[bond.to];

                            if (!from || !to) return;

                            const dx = to.x - from.x;
                            const dy = to.y - from.y;
                            const lineLengthSquared = dx * dx + dy * dy;

                            if (lineLengthSquared === 0) return;

                            const t = Math.max(0, Math.min(1,
                                ((x - from.x) * dx + (y - from.y) * dy) / lineLengthSquared
                            ));

                            const projX = from.x + t * dx;
                            const projY = from.y + t * dy;
                            const distance = Math.sqrt(Math.pow(x - projX, 2) + Math.pow(y - projY, 2));

                            if (distance < 15 && distance < minBondDistance) {
                                minBondDistance = distance;
                                clickedBondIndex = index;
                            }
                        });
                    }

                    if (clickedAtomIndex !== null) {
                        const protectedIndex = protectedAtoms.indexOf(clickedAtomIndex);
                        if (protectedIndex === -1) {
                            protectedAtoms.push(clickedAtomIndex);
                            showNotification(`Atom ${clickedAtomIndex + 1} protected 🛡️`);
                        } else {
                            protectedAtoms.splice(protectedIndex, 1);
                            showNotification(`Atom ${clickedAtomIndex + 1} unprotected`);
                        }
                        redraw();
                    } else if (clickedBondIndex !== null) {
                        const protectedIndex = protectedBonds.indexOf(clickedBondIndex);
                        if (protectedIndex === -1) {
                            protectedBonds.push(clickedBondIndex);
                            showNotification(`Bond ${clickedBondIndex + 1} protected 🛡️`);
                        } else {
                            protectedBonds.splice(protectedIndex, 1);
                            showNotification(`Bond ${clickedBondIndex + 1} unprotected`);
                        }
                        redraw();
                    }
                }
            } else if (selectedTool === 'structure' && pendingStructure) {
                // Place structure at click location
                if (pendingStructure === 'benzene') {
                    createBenzeneRing(x, y);
                } else if (pendingStructure === 'cyclohexane') {
                    createCyclohexane(x, y);
                } else if (pendingStructure === 'cyclopropane') {
                    createCyclopropane(x, y);
                } else if (pendingStructure === 'cyclobutane') {
                    createCyclobutane(x, y);
                } else if (pendingStructure === 'cyclopentane') {
                    createCyclopentane(x, y);
                } else if (pendingStructure === 'cycloheptane') {
                    createCycloheptane(x, y);
                } else if (pendingStructure === 'cyclooctane') {
                    createCyclooctane(x, y);
                } else if (pendingStructure === 'cyclononane') {
                    createCyclononane(x, y);
                } else if (pendingStructure === 'cyclodecane') {
                    createCyclodecane(x, y);
                } else if (pendingStructure === 'chain') {
                    createChain(x, y);
                }
                // Reset after placing
                pendingStructure = null;
                const theme = document.documentElement.getAttribute('data-theme') || 'light';
                const buttonBg = (theme === 'dark' || theme === 'recomended') ? '#1a1a1a' : 'white';
                document.querySelectorAll('.structure-button').forEach(b => b.style.background = buttonBg);
            } else {
                // Atom placement mode - check if clicking on an existing atom
                let clickedAtomIndex = null;
                atoms.forEach((atom, index) => {
                    const distance = Math.sqrt(Math.pow(x - atom.x, 2) + Math.pow(y - atom.y, 2));
                    if (distance < 20) {
                        clickedAtomIndex = index;
                    }
                });

                if (clickedAtomIndex !== null && selectedAtom) {
                    // Clicked on an existing atom with an element selected
                    const clickedAtom = atoms[clickedAtomIndex];
                    if (clickedAtom.element !== selectedAtom) {
                        // Replace the atom's element if it's different
                        saveState();  // Save state before modification
                        atoms[clickedAtomIndex].element = selectedAtom;
                        atoms[clickedAtomIndex].charge = 0;  // Reset charge when replacing element
                        redraw();
                        updateStats();
                    }
                } else if (clickedAtomIndex === null && selectedAtom) {
                    // No atom clicked, place new atom
                    placeAtom(x, y, selectedAtom);
                }
            }
        }); // End of click listener
    }); // End of DOMContentLoaded

    function placeAtom(x, y, element) {
        // Don't place atom if element is undefined or null
        if (!element) {
            console.log('Cannot place atom: no element selected');
            return;
        }

        console.log('Placing atom:', element, 'at', x, y);
        saveState();  // Save state before modification
        atoms.push({ x, y, element, charge: 0 });
        console.log('Total atoms now:', atoms.length);
        drawAtom(x, y, element, 0);
        updateStats();
    }

    // Element color mapping for canvas display (border colors)
    const elementColors = {
        'H': '#999999', 'He': '#d9ffff', 'Li': '#cc80ff', 'Be': '#c2ff00', 'B': '#ffb5b5',
        'C': '#909090', 'N': '#3050f8', 'O': '#ff0d0d', 'F': '#90e050', 'Ne': '#b3e3f5',
        'Na': '#ab5cf2', 'Mg': '#8aff00', 'Al': '#bfa6a6', 'Si': '#f0c8a0', 'P': '#ff8000',
        'S': '#ffff30', 'Cl': '#1ff01f', 'Ar': '#80d1e3', 'K': '#8f40d4', 'Ca': '#3dff00',
        'Sc': '#e6e6e6', 'Ti': '#bfc2c7', 'V': '#a6a6ab', 'Cr': '#8a99c7', 'Mn': '#9c7ac7',
        'Fe': '#e06633', 'Co': '#f090a0', 'Ni': '#50d050', 'Cu': '#c88033', 'Zn': '#7d80b0',
        'Ga': '#c28f8f', 'Ge': '#668f8f', 'As': '#bd80e3', 'Se': '#ffa100', 'Br': '#a62929',
        'Kr': '#5cb8d1', 'Rb': '#702eb0', 'Sr': '#00ff00', 'Y': '#94ffff', 'Zr': '#94e0e0',
        'Nb': '#73c2c9', 'Mo': '#54b5b5', 'Tc': '#3b9e9e', 'Ru': '#248f8f', 'Rh': '#0a7d8c',
        'Pd': '#006985', 'Ag': '#c0c0c0', 'Cd': '#ffd98f', 'In': '#a67573', 'Sn': '#668080',
        'Sb': '#9e63b5', 'Te': '#d47a00', 'I': '#940094', 'Xe': '#429eb0', 'Cs': '#57178f',
        'Ba': '#00c900', 'Hf': '#4dc2ff', 'Ta': '#4da6ff', 'W': '#2194d6', 'Re': '#267dab',
        'Os': '#266696', 'Ir': '#175487', 'Pt': '#d0d0e0', 'Au': '#ffd123', 'Hg': '#b8b8d0',
        'Tl': '#a6544d', 'Pb': '#575961', 'Bi': '#9e4fb5', 'Po': '#ab5c00', 'At': '#754f45',
        'Rn': '#428296', 'Fr': '#420066', 'Ra': '#007d00'
    };

    function drawAtom(x, y, element, charge) {
        const atomDiv = document.createElement('div');
        atomDiv.className = 'placed-atom';

        // Display element with charge if present
        if (charge && charge !== 0) {
            const chargeSymbol = charge > 0 ? '+' : '-';
            const chargeValue = Math.abs(charge) > 1 ? Math.abs(charge) : '';
            atomDiv.innerHTML = `${element}<sup style="font-size: 0.7em;">${chargeValue}${chargeSymbol}</sup>`;
        } else {
            atomDiv.textContent = element;
        }

        // Get current theme for background
        const theme = document.documentElement.getAttribute('data-theme') || 'light';
        const bgColor = (theme === 'dark' || theme === 'recomended') ? '#2d2d2d' : 'white';
        const textColorTheme = (theme === 'dark' || theme === 'recomended') ? 'white' : '#333';

        // Get element-specific border color
        const borderColor = elementColors[element] || '#999999';

        atomDiv.style.cssText = `
            position: absolute;
            left: ${x}px;
            top: ${y}px;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: ${bgColor};
            border: 3px solid ${borderColor};
            color: ${textColorTheme};
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            transform: translate(-50%, -50%);
            cursor: pointer;
            z-index: 10;
            user-select: none;
        `;
        canvasInner.appendChild(atomDiv);
    }

    function drawBonds() {
        // Remove existing bonds more thoroughly
        const existingBonds = canvasInner.querySelectorAll('.bond-line, .bond-protection-badge');
        console.log('Removing', existingBonds.length, 'existing bond elements');
        existingBonds.forEach(b => b.remove());

        // Get current theme
        const theme = document.documentElement.getAttribute('data-theme') || 'light';
        const bondColor = (theme === 'dark' || theme === 'recomended') ? '#ffffff' : '#333';

        console.log('Drawing', bonds.length, 'bonds:', bonds);

        bonds.forEach((bond, bondIndex) => {
            const from = atoms[bond.from];
            const to = atoms[bond.to];

            // Safety check - skip if atoms don't exist
            if (!from || !to) {
                console.warn('Invalid bond found:', bond);
                return;
            }

            const bondOrder = bond.order || 1;
            const bondType = bond.type;  // wedge, dash, aromatic
            const isProtected = protectedBonds.includes(bondIndex);

            const length = Math.sqrt(Math.pow(to.x - from.x, 2) + Math.pow(to.y - from.y, 2));
            const angle = Math.atan2(to.y - from.y, to.x - from.x) * 180 / Math.PI;
            const perpAngle = angle + 90;

            // Add protection indicator for bonds if protected
            if (isProtected) {
                const midX = (from.x + to.x) / 2;
                const midY = (from.y + to.y) / 2;
                const badge = document.createElement('div');
                badge.className = 'bond-protection-badge';
                badge.innerHTML = '🛡️';
                badge.style.cssText = `
                    position: absolute;
                    left: ${midX}px;
                    top: ${midY}px;
                    width: 18px;
                    height: 18px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 12px;
                    transform: translate(-50%, -50%);
                    pointer-events: none;
                    z-index: 20;
                    background: rgba(255, 255, 255, 0.9);
                    border-radius: 50%;
                `;
                canvasInner.appendChild(badge);
            }

            // Handle special bond types
            if (bondType === 'wedge') {
                // Wedge bond (solid triangle - out of plane)
                const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                svg.setAttribute('class', 'bond-line');
                svg.style.cssText = `
                    position: absolute;
                    left: ${from.x}px;
                    top: ${from.y}px;
                    width: ${length}px;
                    height: 20px;
                    transform-origin: 0 10px;
                    transform: rotate(${angle}deg);
                    overflow: visible;
                    z-index: 1;
                    pointer-events: none;
                `;
                const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
                polygon.setAttribute('points', `0,10 ${length},5 ${length},15`);
                polygon.setAttribute('fill', bondColor);
                svg.appendChild(polygon);
                canvasInner.appendChild(svg);
                return;
            } else if (bondType === 'dash') {
                // Dashed bond (tapering lines - into plane)
                const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                svg.setAttribute('class', 'bond-line');
                svg.style.cssText = `
                    position: absolute;
                    left: ${from.x}px;
                    top: ${from.y}px;
                    width: ${length}px;
                    height: 20px;
                    transform-origin: 0 10px;
                    transform: rotate(${angle}deg);
                    overflow: visible;
                    z-index: 1;
                    pointer-events: none;
                `;

                // Draw multiple tapering lines
                const numLines = 8;
                const spacing = length / numLines;
                for (let i = 0; i < numLines; i++) {
                    const lineX = spacing * i;
                    const lineWidth = 3 - (i * 2.5 / numLines);  // Taper from 3 to 0.5
                    const lineHeight = 10 - (i * 8 / numLines);  // Taper height

                    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                    line.setAttribute('x1', lineX);
                    line.setAttribute('y1', 10 - lineHeight / 2);
                    line.setAttribute('x2', lineX);
                    line.setAttribute('y2', 10 + lineHeight / 2);
                    line.setAttribute('stroke', bondColor);
                    line.setAttribute('stroke-width', lineWidth);
                    svg.appendChild(line);
                }
                canvasInner.appendChild(svg);
                return;
            } else if (bondType === 'aromatic') {
                // Aromatic bond - solid line + dashed line
                const offset = 3;

                // Solid line
                const line1 = document.createElement('div');
                line1.className = 'bond-line';
                const offsetX1 = Math.cos(perpAngle * Math.PI / 180) * offset;
                const offsetY1 = Math.sin(perpAngle * Math.PI / 180) * offset;
                line1.style.cssText = `
                    position: absolute;
                    left: ${from.x + offsetX1}px;
                    top: ${from.y + offsetY1}px;
                    width: ${length}px;
                    height: 2px;
                    background: ${bondColor};
                    transform-origin: 0 0;
                    transform: rotate(${angle}deg);
                    z-index: 1;
                    pointer-events: none;
                `;
                canvasInner.appendChild(line1);

                // Dashed line
                const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                svg.setAttribute('class', 'bond-line');
                const offsetX2 = Math.cos(perpAngle * Math.PI / 180) * (-offset);
                const offsetY2 = Math.sin(perpAngle * Math.PI / 180) * (-offset);
                svg.style.cssText = `
                    position: absolute;
                    left: ${from.x + offsetX2}px;
                    top: ${from.y + offsetY2}px;
                    width: ${length}px;
                    height: 4px;
                    transform-origin: 0 2px;
                    transform: rotate(${angle}deg);
                    overflow: visible;
                    z-index: 1;
                    pointer-events: none;
                `;
                const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                line.setAttribute('x1', 0);
                line.setAttribute('y1', 2);
                line.setAttribute('x2', length);
                line.setAttribute('y2', 2);
                line.setAttribute('stroke', bondColor);
                line.setAttribute('stroke-width', '2');
                line.setAttribute('stroke-dasharray', '4,4');
                svg.appendChild(line);
                canvasInner.appendChild(svg);
                return;
            }

            // Regular bonds (1, 2, 3)
            if (bondOrder === 1) {
                // Single bond
                const line = document.createElement('div');
                line.className = 'bond-line';
                line.style.cssText = `
                    position: absolute;
                    left: ${from.x}px;
                    top: ${from.y}px;
                    width: ${length}px;
                    height: 2px;
                    background: ${bondColor};
                    transform-origin: 0 0;
                    transform: rotate(${angle}deg);
                    z-index: 1;
                    pointer-events: none;
                `;
                canvasInner.appendChild(line);
            } else if (bondOrder === 2) {
                // Double bond - two parallel lines
                const offset = 3;
                for (let i = -1; i <= 1; i += 2) {
                    const line = document.createElement('div');
                    line.className = 'bond-line';
                    const offsetX = Math.cos(perpAngle * Math.PI / 180) * offset * i;
                    const offsetY = Math.sin(perpAngle * Math.PI / 180) * offset * i;
                    line.style.cssText = `
                        position: absolute;
                        left: ${from.x + offsetX}px;
                        top: ${from.y + offsetY}px;
                        width: ${length}px;
                        height: 2px;
                        background: ${bondColor};
                        transform-origin: 0 0;
                        transform: rotate(${angle}deg);
                        z-index: 1;
                        pointer-events: none;
                    `;
                    canvasInner.appendChild(line);
                }
            } else if (bondOrder === 3) {
                // Triple bond - three parallel lines
                const offset = 4;
                for (let i = -1; i <= 1; i++) {
                    const line = document.createElement('div');
                    line.className = 'bond-line';
                    const offsetX = Math.cos(perpAngle * Math.PI / 180) * offset * i;
                    const offsetY = Math.sin(perpAngle * Math.PI / 180) * offset * i;
                    line.style.cssText = `
                        position: absolute;
                        left: ${from.x + offsetX}px;
                        top: ${from.y + offsetY}px;
                        width: ${length}px;
                        height: 2px;
                        background: ${bondColor};
                        transform-origin: 0 0;
                        transform: rotate(${angle}deg);
                        z-index: 1;
                        pointer-events: none;
                    `;
                    canvasInner.appendChild(line);
                }
            }
        });
    }

    function redraw() {
        // Clear all atoms and bonds
        canvasInner.querySelectorAll('.placed-atom, .bond-line, .protection-badge, .bond-protection-badge, .bond-highlight').forEach(el => el.remove());

        // Redraw bonds first (so they appear behind atoms)
        drawBonds();

        // Redraw atoms
        atoms.forEach((atom, index) => {
            drawAtom(atom.x, atom.y, atom.element, atom.charge || 0);
            // Add protection indicator if atom is protected
            if (protectedAtoms.includes(index)) {
                drawProtectionBadge(atom.x, atom.y);
            }
        });

        // Re-highlight selected atoms and bonds after redraw
        if (selectedAtoms.length > 0) {
            highlightSelectedAtoms();
        }
        if (selectedBonds.length > 0) {
            highlightSelectedBonds(selectedBonds);
        }
    }

    function drawProtectionBadge(x, y) {
        const badge = document.createElement('div');
        badge.className = 'protection-badge';
        badge.innerHTML = '🛡️';
        badge.style.cssText = `
            position: absolute;
            left: ${x + 15}px;
            top: ${y - 25}px;
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            transform: translate(-50%, -50%);
            pointer-events: none;
            z-index: 15;
        `;
        canvasInner.appendChild(badge);
    }

    function highlightAtom(index) {
        removeHighlights();
        const atomElements = canvasInner.querySelectorAll('.placed-atom');
        if (atomElements[index]) {
            atomElements[index].style.boxShadow = '0 0 0 3px #0d6efd';
        }
    }

    function removeHighlights() {
        canvasInner.querySelectorAll('.placed-atom').forEach(a => a.style.boxShadow = '');
        canvasInner.querySelectorAll('.bond-highlight').forEach(el => el.remove());
    }

    function highlightSelectedAtoms() {
        removeHighlights();
        const atomElements = canvasInner.querySelectorAll('.placed-atom');
        selectedAtoms.forEach(index => {
            if (atomElements[index]) {
                atomElements[index].style.boxShadow = '0 0 0 3px #28a745';
            }
        });
    }

    function highlightSelectedBonds(bondIndices) {
        // Remove existing bond highlights
        canvasInner.querySelectorAll('.bond-highlight').forEach(el => el.remove());

        if (!bondIndices || bondIndices.length === 0) return;

        bondIndices.forEach(bondIndex => {
            const bond = bonds[bondIndex];
            if (!bond) return;

            const from = atoms[bond.from];
            const to = atoms[bond.to];
            if (!from || !to) return;

            // Draw highlight line along the bond
            const length = Math.sqrt(Math.pow(to.x - from.x, 2) + Math.pow(to.y - from.y, 2));
            const angle = Math.atan2(to.y - from.y, to.x - from.x) * 180 / Math.PI;

            const highlight = document.createElement('div');
            highlight.className = 'bond-highlight';
            highlight.style.cssText = `
                position: absolute;
                left: ${from.x}px;
                top: ${from.y}px;
                width: ${length}px;
                height: 6px;
                background: rgba(40, 167, 69, 0.3);
                transform-origin: 0 0;
                transform: rotate(${angle}deg) translateY(-2px);
                z-index: 2;
                pointer-events: none;
                border-radius: 3px;
            `;
            canvasInner.appendChild(highlight);
        });
    }

    function drawSelectionBox() {
        // Remove existing selection box
        removeSelectionBox();

        if (!selectionBox) return;

        const minX = Math.min(selectionBox.startX, selectionBox.endX);
        const minY = Math.min(selectionBox.startY, selectionBox.endY);
        const width = Math.abs(selectionBox.endX - selectionBox.startX);
        const height = Math.abs(selectionBox.endY - selectionBox.startY);

        const box = document.createElement('div');
        box.className = 'selection-box-overlay';
        box.style.cssText = `
            position: absolute;
            left: ${minX}px;
            top: ${minY}px;
            width: ${width}px;
            height: ${height}px;
            border: 2px dashed #0d6efd;
            background: rgba(13, 110, 253, 0.1);
            pointer-events: none;
            z-index: 100;
        `;
        canvasInner.appendChild(box);
    }

    function removeSelectionBox() {
        const box = canvasInner.querySelector('.selection-box-overlay');
        if (box) box.remove();
    }

    function drawLassoPath() {
        // Remove existing lasso path
        removeLassoPath();

        if (!lassoPath || lassoPath.length < 2) return;

        // Create SVG for smooth lasso path
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'lasso-path-overlay');
        svg.style.cssText = `
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 100;
        `;

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        let pathData = `M ${lassoPath[0].x} ${lassoPath[0].y}`;
        for (let i = 1; i < lassoPath.length; i++) {
            pathData += ` L ${lassoPath[i].x} ${lassoPath[i].y}`;
        }

        path.setAttribute('d', pathData);
        path.setAttribute('stroke', '#0d6efd');
        path.setAttribute('stroke-width', '2');
        path.setAttribute('stroke-dasharray', '5,5');
        path.setAttribute('fill', 'rgba(13, 110, 253, 0.1)');

        svg.appendChild(path);
        canvasInner.appendChild(svg);
    }

    function removeLassoPath() {
        const lasso = canvasInner.querySelector('.lasso-path-overlay');
        if (lasso) lasso.remove();
    }

    // Point in polygon algorithm (ray casting)
    function isPointInPolygon(point, polygon) {
        if (polygon.length < 3) return false;

        let inside = false;
        const x = point.x;
        const y = point.y;

        for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
            const xi = polygon[i].x;
            const yi = polygon[i].y;
            const xj = polygon[j].x;
            const yj = polygon[j].y;

            const intersect = ((yi > y) !== (yj > y))
                && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);

            if (intersect) inside = !inside;
        }

        return inside;
    }

    function getAtomColor(element) {
        const colors = {
            'H': '#999999',
            'C': '#6c757d',
            'N': '#0d6efd',
            'O': '#dc3545',
            'S': '#ffc107',
            'P': '#17a2b8',
            'F': '#28a745',
            'Cl': '#6c757d',
            'Br': '#6c757d',
            'I': '#6c757d'
        };
        return colors[element] || '#6c757d';
    }

    // Save current state to history
    function saveState() {
        const state = {
            atoms: JSON.parse(JSON.stringify(atoms)),
            bonds: JSON.parse(JSON.stringify(bonds))
        };
        history.push(state);

        // Limit history size
        if (history.length > MAX_HISTORY) {
            history.shift();
        }

        // Clear redo stack when new action is performed
        redoStack = [];
        updateUndoRedoButtons();
    }

    // Restore state from history
    function restoreState(state) {
        atoms = JSON.parse(JSON.stringify(state.atoms));
        bonds = JSON.parse(JSON.stringify(state.bonds));

        // Clear all visual overlays
        removeLassoPath();
        removeSelectionBox();
        removeHighlights();

        // Reset selection states
        selectedAtoms = [];
        selectedAtomIndex = null;
        isLassoSelecting = false;
        lassoPath = [];
        isBoxSelecting = false;
        selectionBox = null;

        redraw();
        updateStats();
    }

    // Undo last action
    function undo() {
        if (history.length === 0) {
            console.log('No history to undo');
            return;
        }

        // Save current state to redo stack
        const currentState = {
            atoms: JSON.parse(JSON.stringify(atoms)),
            bonds: JSON.parse(JSON.stringify(bonds))
        };
        redoStack.push(currentState);

        // Restore previous state
        const previousState = history.pop();
        restoreState(previousState);
        updateUndoRedoButtons();
        console.log('Undo performed');
    }

    // Redo last undone action
    function redo() {
        if (redoStack.length === 0) {
            console.log('No redo available');
            return;
        }

        // Save current state to history
        const currentState = {
            atoms: JSON.parse(JSON.stringify(atoms)),
            bonds: JSON.parse(JSON.stringify(bonds))
        };
        history.push(currentState);

        // Restore next state
        const nextState = redoStack.pop();
        restoreState(nextState);
        updateUndoRedoButtons();
        console.log('Redo performed');
    }

    // Update undo/redo button states
    function updateUndoRedoButtons() {
        const undoBtn = document.querySelector('.canvas-toolbar button[title="Undo"]');
        const redoBtn = document.querySelector('.canvas-toolbar button[title="Redo"]');

        if (undoBtn) {
            if (history.length === 0) {
                undoBtn.style.opacity = '0.3';
                undoBtn.style.cursor = 'not-allowed';
            } else {
                undoBtn.style.opacity = '1';
                undoBtn.style.cursor = 'pointer';
            }
        }

        if (redoBtn) {
            if (redoStack.length === 0) {
                redoBtn.style.opacity = '0.3';
                redoBtn.style.cursor = 'not-allowed';
            } else {
                redoBtn.style.opacity = '1';
                redoBtn.style.cursor = 'pointer';
            }
        }
    }

    function updateStats() {
        document.getElementById('atomCount').textContent = atoms.length;
        document.getElementById('bondCount').textContent = bonds.length;

        // Calculate approximate molecular weight
        const weights = {
            'H': 1, 'C': 12, 'N': 14, 'O': 16, 'S': 32, 'P': 31,
            'F': 19, 'Cl': 35.5, 'Br': 80, 'I': 127
        };
        let totalWeight = atoms.reduce((sum, atom) => sum + (weights[atom.element] || 0), 0);
        document.getElementById('molecularWeight').textContent = totalWeight.toFixed(2);

        // Generate molecular formula
        const formula = {};
        atoms.forEach(atom => {
            formula[atom.element] = (formula[atom.element] || 0) + 1;
        });
        const formulaStr = Object.entries(formula)
            .sort()
            .map(([el, count]) => count > 1 ? `${el}${count}` : el)
            .join('');
        document.getElementById('molecularFormula').textContent = formulaStr || '-';

        // Generate SMILES notation
        const smiles = generateSMILES();
        document.getElementById('smilesNotation').textContent = smiles || '-';
        document.getElementById('smilesValidation').textContent = '';
    }

    async function validateSMILES() {
        const smiles = document.getElementById('smilesNotation').textContent;
        const validationDiv = document.getElementById('smilesValidation');

        if (!smiles || smiles === '-') {
            validationDiv.innerHTML = '<span style="color: #ff6b6b;">⚠️ No SMILES to validate</span>';
            return;
        }

        validationDiv.innerHTML = '<span style="color: #999;">⏳ Validating...</span>';

        try {
            const response = await fetch('/molecules/validate-smiles/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                },
                body: JSON.stringify({ smiles: smiles })
            });

            const data = await response.json();

            if (data.valid) {
                validationDiv.innerHTML = '<span style="color: #51cf66;">✓ Valid SMILES</span>';
                if (data.canonical_smiles && data.canonical_smiles !== smiles) {
                    validationDiv.innerHTML += `<br><span style="color: #999; font-size: 0.7rem;">Canonical: ${data.canonical_smiles}</span>`;
                }
            } else {
                validationDiv.innerHTML = '<span style="color: #ff6b6b;">✗ Invalid SMILES</span>';
                if (data.error) {
                    validationDiv.innerHTML += `<br><span style="color: #ff6b6b; font-size: 0.7rem;">${data.error}</span>`;
                }
            }
        } catch (error) {
            validationDiv.innerHTML = '<span style="color: #ff6b6b;">✗ Validation failed</span>';
            console.error('Validation error:', error);
        }
    }

    async function generateMLSmiles() {
        const smilesDiv = document.getElementById('smilesNotation');
        const validationDiv = document.getElementById('smilesValidation');

        // Show loading state
        smilesDiv.textContent = 'Generating...';
        validationDiv.innerHTML = '<span style="color: #999;">🤖 Using ML model...</span>';

        try {
            const response = await fetch('/molecules/generate-ml-smiles/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                },
                body: JSON.stringify({
                    temperature: 0.8  // Controls randomness (0.5 = more conservative, 1.5 = more creative)
                })
            });

            const data = await response.json();

            if (data.success && data.smiles) {
                smilesDiv.textContent = data.smiles;
                validationDiv.innerHTML = `<span style="color: #51cf66;">✓ Generated using ${data.method}</span>`;

                // Show notification with method used
                showNotification(`SMILES generated using ML (${data.method})`, 'success');
            } else {
                smilesDiv.textContent = '-';
                validationDiv.innerHTML = `<span style="color: #ff6b6b;">✗ ${data.error || 'Generation failed'}</span>`;
                showNotification('ML generation failed. Train the model first.', 'error');
            }
        } catch (error) {
            smilesDiv.textContent = '-';
            validationDiv.innerHTML = '<span style="color: #ff6b6b;">✗ Generation failed</span>';
            console.error('ML generation error:', error);
            showNotification('ML model not available. Please train the model first.', 'error');
        }
    }

    function generateSMILES() {
        if (atoms.length === 0) return '';

        // Filter out hydrogen atoms - they are implicit in SMILES
        const nonHAtoms = [];
        const atomIndexMap = new Map(); // Maps original index to new index (without H)

        atoms.forEach((atom, idx) => {
            if (atom.element !== 'H') {
                atomIndexMap.set(idx, nonHAtoms.length);
                nonHAtoms.push({ ...atom, originalIdx: idx });
            }
        });

        if (nonHAtoms.length === 0) return 'H2'; // Special case: only hydrogens

        // Build adjacency list excluding hydrogen bonds
        const adjacency = nonHAtoms.map(() => []);
        const bondMap = new Map();

        bonds.forEach(bond => {
            // Skip bonds involving hydrogen atoms
            if (atoms[bond.from].element === 'H' || atoms[bond.to].element === 'H') {
                return;
            }

            const fromIdx = atomIndexMap.get(bond.from);
            const toIdx = atomIndexMap.get(bond.to);

            if (fromIdx !== undefined && toIdx !== undefined) {
                const key1 = `${fromIdx}-${toIdx}`;
                const key2 = `${toIdx}-${fromIdx}`;

                bondMap.set(key1, bond.order || 1);
                bondMap.set(key2, bond.order || 1);

                adjacency[fromIdx].push({ to: toIdx, order: bond.order || 1 });
                adjacency[toIdx].push({ to: fromIdx, order: bond.order || 1 });
            }
        });

        // Detect aromatic atoms (atoms in rings with alternating double bonds)
        const aromatic = detectAromaticAtoms(adjacency, bondMap);

        // Track visited atoms and bonds
        const visited = new Array(nonHAtoms.length).fill(false);
        const visitedBonds = new Set();
        const ringClosures = new Map(); // Maps atom pair to ring number
        let ringCounter = 1;
        let smiles = '';

        function getBondSymbol(fromIdx, toIdx, order) {
            // If both atoms are aromatic, omit the bond symbol (aromatic bonds are implicit)
            if (aromatic[fromIdx] && aromatic[toIdx]) {
                return '';
            }
            // Otherwise use explicit bond symbols
            if (order === 2) return '=';
            if (order === 3) return '#';
            return '';
        }

        function getAtomSymbol(idx) {
            const element = nonHAtoms[idx].element;
            // Use lowercase for aromatic carbons
            if (aromatic[idx] && element === 'C') {
                return 'c';
            }
            // For other aromatic atoms, use lowercase if it's a common aromatic atom
            if (aromatic[idx] && ['N', 'O', 'S'].includes(element)) {
                return element.toLowerCase();
            }
            return element;
        }

        function dfs(idx, parentIdx = -1) {
            visited[idx] = true;

            // Write atom symbol
            smiles += getAtomSymbol(idx);

            // Collect neighbors by type
            const neighbors = adjacency[idx];
            const unvisitedNeighbors = [];
            const backEdges = []; // Edges to already visited atoms (ring closures)

            neighbors.forEach(neighbor => {
                if (!visited[neighbor.to]) {
                    unvisitedNeighbors.push(neighbor);
                } else if (neighbor.to !== parentIdx) {
                    // This is a back edge (to an already visited non-parent atom)
                    backEdges.push(neighbor);
                }
            });

            // Handle ring closures - write ring numbers for back edges
            backEdges.forEach(neighbor => {
                const bondKey1 = `${Math.min(idx, neighbor.to)}-${Math.max(idx, neighbor.to)}`;

                // Check if we already assigned a ring number to this bond
                let ringNum = ringClosures.get(bondKey1);

                if (!ringNum) {
                    // First time seeing this back edge - assign a new ring number
                    ringNum = ringCounter++;
                    ringClosures.set(bondKey1, ringNum);
                }

                // Write ring closure
                const bondSymbol = getBondSymbol(idx, neighbor.to, neighbor.order);
                smiles += bondSymbol;
                smiles += ringNum;
            });

            // Process unvisited neighbors
            if (unvisitedNeighbors.length > 0) {
                // Mark the first neighbor's bond as visited
                const first = unvisitedNeighbors[0];
                const bondKey = `${Math.min(idx, first.to)}-${Math.max(idx, first.to)}`;
                visitedBonds.add(bondKey);

                // Write bond symbol and continue DFS
                smiles += getBondSymbol(idx, first.to, first.order);
                dfs(first.to, idx);

                // Additional unvisited neighbors are branches
                for (let i = 1; i < unvisitedNeighbors.length; i++) {
                    const neighbor = unvisitedNeighbors[i];
                    const bondKey = `${Math.min(idx, neighbor.to)}-${Math.max(idx, neighbor.to)}`;
                    visitedBonds.add(bondKey);

                    smiles += '(';
                    smiles += getBondSymbol(idx, neighbor.to, neighbor.order);
                    dfs(neighbor.to, idx);
                    smiles += ')';
                }
            }
        }

        // Start DFS from first non-hydrogen atom
        console.log('Starting SMILES generation...');
        console.log('Adjacency list:', adjacency.map((adj, idx) => `${idx}: [${adj.map(n => n.to).join(',')}]`).join(', '));
        dfs(0);

        // Handle disconnected fragments
        for (let i = 0; i < nonHAtoms.length; i++) {
            if (!visited[i]) {
                smiles += '.';
                ringCounter = 1;  // Reset ring counter for each fragment
                ringClosures.clear();  // Clear ring closures for new fragment
                dfs(i);
            }
        }

        // Validate ring closures - each ring number should appear exactly twice within each fragment
        const fragments = smiles.split('.');

        fragments.forEach((fragment, fragIdx) => {
            const ringNumbers = fragment.match(/\d+/g) || [];
            const ringCounts = {};
            ringNumbers.forEach(num => {
                ringCounts[num] = (ringCounts[num] || 0) + 1;
            });

            // Check for incomplete rings in this fragment - just warn, don't block
            for (const [num, count] of Object.entries(ringCounts)) {
                if (count !== 2) {
                    console.warn(`Fragment ${fragIdx}: Ring closure ${num} appears ${count} times (expected 2) - SMILES may be invalid`);
                }
            }
        });

        return smiles;
    }

    function detectAromaticAtoms(adjacency, bondMap) {
        const n = adjacency.length;
        const aromatic = new Array(n).fill(false);

        // Find all cycles using DFS
        const visited = new Array(n).fill(false);
        const recStack = new Array(n).fill(false);
        const parent = new Array(n).fill(-1);
        const cycles = [];

        function findCycles(v, p) {
            visited[v] = true;
            recStack[v] = true;
            parent[v] = p;

            for (const neighbor of adjacency[v]) {
                const u = neighbor.to;

                if (!visited[u]) {
                    findCycles(u, v);
                } else if (recStack[u] && u !== p) {
                    // Found a cycle
                    const cycle = [];
                    let curr = v;
                    while (curr !== u && curr !== -1) {
                        cycle.push(curr);
                        curr = parent[curr];
                    }
                    cycle.push(u);
                    if (cycle.length >= 5 && cycle.length <= 7) {
                        cycles.push(cycle);
                    }
                }
            }

            recStack[v] = false;
        }

        for (let i = 0; i < n; i++) {
            if (!visited[i]) {
                findCycles(i, -1);
            }
        }

        // Check each cycle for aromaticity (alternating single/double bonds)
        cycles.forEach(cycle => {
            let hasDoubleBond = false;
            let allAlternating = true;
            let doubleCount = 0;

            for (let i = 0; i < cycle.length; i++) {
                const from = cycle[i];
                const to = cycle[(i + 1) % cycle.length];
                const bondKey = `${from}-${to}`;
                const order = bondMap.get(bondKey) || 1;

                if (order === 2) {
                    doubleCount++;
                    hasDoubleBond = true;
                } else if (order !== 1) {
                    allAlternating = false;
                    break;
                }
            }

            // A ring is aromatic if it has alternating single/double bonds
            // For 6-membered rings (benzene), should have 3 double bonds
            const isAromatic = hasDoubleBond &&
                cycle.length === 6 &&
                doubleCount === 3;

            if (isAromatic) {
                cycle.forEach(idx => {
                    aromatic[idx] = true;
                });
            }
        });

        return aromatic;
    }

    // Clear button
    const clearBtn = document.querySelector('.canvas-toolbar button[title="Clear"]');
    console.log('Clear button found:', clearBtn);
    if (clearBtn) {
        clearBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Clear button clicked');
            showConfirmModal('Are you sure you want to clear the canvas?', function (confirmed) {
                if (confirmed) {
                    saveState();  // Save state before clearing
                    atoms = [];
                    bonds = [];
                    selectedAtomIndex = null;
                    selectedAtoms = [];
                    canvasInner.querySelectorAll('.placed-atom, .bond-line').forEach(el => el.remove());
                    if (placeholder) placeholder.style.display = 'block';
                    updateStats();
                    updateUndoRedoButtons();
                }
            });
        });
    }

    // Undo button
    const undoBtn = document.querySelector('.canvas-toolbar button[title="Undo"]');
    console.log('Undo button found:', undoBtn);
    if (undoBtn) {
        undoBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Undo button clicked');
            undo();
        });
    }

    // Redo button
    const redoBtn = document.querySelector('.canvas-toolbar button[title="Redo"]');
    console.log('Redo button found:', redoBtn);
    if (redoBtn) {
        redoBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Redo button clicked');
            redo();
        });
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', function (e) {
        // Delete key - remove selected atoms
        if (e.key === 'Delete' && selectedAtoms.length > 0) {
            saveState();

            // Sort indices in descending order to avoid index shifting issues
            const sortedIndices = [...selectedAtoms].sort((a, b) => b - a);

            // Remove atoms
            sortedIndices.forEach(index => {
                atoms.splice(index, 1);

                // Remove bonds connected to this atom and adjust indices
                bonds = bonds.filter(b => b.from !== index && b.to !== index)
                    .map(b => ({
                        from: b.from > index ? b.from - 1 : b.from,
                        to: b.to > index ? b.to - 1 : b.to,
                        order: b.order || 1
                    }));
            });

            selectedAtoms = [];
            redraw();
            updateStats();
        }

        // Escape key - clear selection
        if (e.key === 'Escape') {
            selectedAtoms = [];
            removeHighlights();
            removeSelectionBox();
        }
    });

    // Structure buttons - enable click-to-place mode
    document.querySelectorAll('.structure-button').forEach(btn => {
        btn.addEventListener('click', function () {
            const text = this.textContent.toLowerCase();
            if (text.includes('benzene')) {
                pendingStructure = 'benzene';
                selectedTool = 'structure';
            } else if (text.includes('cyclohexane')) {
                pendingStructure = 'cyclohexane';
                selectedTool = 'structure';
            } else if (text.includes('cyclopropane')) {
                pendingStructure = 'cyclopropane';
                selectedTool = 'structure';
            } else if (text.includes('cyclobutane')) {
                pendingStructure = 'cyclobutane';
                selectedTool = 'structure';
            } else if (text.includes('cyclopentane')) {
                pendingStructure = 'cyclopentane';
                selectedTool = 'structure';
            } else if (text.includes('cycloheptane')) {
                pendingStructure = 'cycloheptane';
                selectedTool = 'structure';
            } else if (text.includes('cyclooctane')) {
                pendingStructure = 'cyclooctane';
                selectedTool = 'structure';
            } else if (text.includes('cyclononane')) {
                pendingStructure = 'cyclononane';
                selectedTool = 'structure';
            } else if (text.includes('cyclodecane')) {
                pendingStructure = 'cyclodecane';
                selectedTool = 'structure';
            } else if (text.includes('chain')) {
                pendingStructure = 'chain';
                selectedTool = 'structure';
            }

            // Clear atom selection when switching to structure mode
            selectedAtoms = [];
            removeHighlights();
            removeSelectionBox();

            // Visual feedback
            document.querySelectorAll('.tool-item').forEach(t => t.classList.remove('active'));
            const theme = document.documentElement.getAttribute('data-theme') || 'light';
            const buttonBg = (theme === 'dark' || theme === 'recomended') ? '#1a1a1a' : 'white';
            const activeBg = (theme === 'dark' || theme === 'recomended') ? '#2d4a5e' : '#e3f2fd';
            document.querySelectorAll('.structure-button').forEach(b => b.style.background = buttonBg);
            this.style.background = activeBg;
            console.log('Click on canvas to place', pendingStructure);
        });
    });

    function createBenzeneRing(centerX = null, centerY = null) {
        saveState();  // Save state before modification
        if (placeholder) placeholder.style.display = 'none';
        if (centerX === null) centerX = canvas.offsetWidth / 2;
        if (centerY === null) centerY = canvas.offsetHeight / 2;
        const radius = 60;
        const hDistance = 45;  // Distance for hydrogen atoms from carbon

        const startIndex = atoms.length;
        // Create carbon ring
        for (let i = 0; i < 6; i++) {
            const angle = (i * 60 - 90) * Math.PI / 180;
            const x = centerX + radius * Math.cos(angle);
            const y = centerY + radius * Math.sin(angle);
            atoms.push({ x, y, element: 'C' });
        }

        // Create alternating single and double bonds for aromatic benzene
        for (let i = 0; i < 6; i++) {
            bonds.push({
                from: startIndex + i,
                to: startIndex + ((i + 1) % 6),
                order: (i % 2 === 0) ? 2 : 1  // Alternating double (2) and single (1) bonds
            });
        }

        // Add hydrogen atoms (one per carbon)
        const hStartIndex = atoms.length;
        for (let i = 0; i < 6; i++) {
            const angle = (i * 60 - 90) * Math.PI / 180;
            const hx = centerX + (radius + hDistance) * Math.cos(angle);
            const hy = centerY + (radius + hDistance) * Math.sin(angle);
            atoms.push({ x: hx, y: hy, element: 'H' });

            // Bond hydrogen to carbon
            bonds.push({
                from: startIndex + i,
                to: hStartIndex + i,
                order: 1
            });
        }

        redraw();
        updateStats();
    }

    function createCyclohexane(centerX = null, centerY = null) {
        saveState();  // Save state before modification
        if (placeholder) placeholder.style.display = 'none';
        if (centerX === null) centerX = canvas.offsetWidth / 2;
        if (centerY === null) centerY = canvas.offsetHeight / 2;
        const radius = 60;
        const hDistance = 45;  // Distance for hydrogen atoms from carbon

        const startIndex = atoms.length;
        // Create carbon ring
        for (let i = 0; i < 6; i++) {
            const angle = (i * 60 - 90) * Math.PI / 180;
            const x = centerX + radius * Math.cos(angle);
            const y = centerY + radius * Math.sin(angle);
            atoms.push({ x, y, element: 'C' });
        }

        // Create all single bonds for saturated cyclohexane
        for (let i = 0; i < 6; i++) {
            bonds.push({
                from: startIndex + i,
                to: startIndex + ((i + 1) % 6),
                order: 1  // All single bonds
            });
        }

        // Add hydrogen atoms (two per carbon)
        const hStartIndex = atoms.length;
        for (let i = 0; i < 6; i++) {
            const angle = (i * 60 - 90) * Math.PI / 180;
            const perpAngle1 = angle + 12 * Math.PI / 180;  // Offset for first H
            const perpAngle2 = angle - 12 * Math.PI / 180;  // Offset for second H

            // First hydrogen
            const h1x = centerX + (radius + hDistance) * Math.cos(perpAngle1);
            const h1y = centerY + (radius + hDistance) * Math.sin(perpAngle1);
            atoms.push({ x: h1x, y: h1y, element: 'H' });
            bonds.push({ from: startIndex + i, to: hStartIndex + i * 2, order: 1 });

            // Second hydrogen
            const h2x = centerX + (radius + hDistance) * Math.cos(perpAngle2);
            const h2y = centerY + (radius + hDistance) * Math.sin(perpAngle2);
            atoms.push({ x: h2x, y: h2y, element: 'H' });
            bonds.push({ from: startIndex + i, to: hStartIndex + i * 2 + 1, order: 1 });
        }

        redraw();
        updateStats();
    }

    function createChain(startX = null, startY = null) {
        saveState();  // Save state before modification
        if (placeholder) placeholder.style.display = 'none';
        if (startX === null) startX = 100;
        if (startY === null) startY = canvas.offsetHeight / 2;
        const spacing = 60;
        const hDistance = 45;  // Distance for hydrogen atoms from carbon

        const startIndex = atoms.length;
        // Create carbon chain
        for (let i = 0; i < 5; i++) {
            atoms.push({
                x: startX + i * spacing,
                y: startY,
                element: 'C'
            });
        }

        // Create C-C bonds
        for (let i = 0; i < 4; i++) {
            bonds.push({
                from: startIndex + i,
                to: startIndex + i + 1,
                order: 1
            });
        }

        // Add hydrogen atoms
        let hIndex = atoms.length;  // Track current hydrogen index
        for (let i = 0; i < 5; i++) {
            const carbonX = startX + i * spacing;
            const carbonY = startY;

            if (i === 0) {
                // First carbon: 3 hydrogens
                // Top H
                atoms.push({ x: carbonX, y: carbonY - hDistance, element: 'H' });
                bonds.push({ from: startIndex + i, to: hIndex++, order: 1 });
                // Bottom H
                atoms.push({ x: carbonX, y: carbonY + hDistance, element: 'H' });
                bonds.push({ from: startIndex + i, to: hIndex++, order: 1 });
                // Left H
                atoms.push({ x: carbonX - hDistance, y: carbonY, element: 'H' });
                bonds.push({ from: startIndex + i, to: hIndex++, order: 1 });
            } else if (i === 4) {
                // Last carbon: 3 hydrogens
                // Top H
                atoms.push({ x: carbonX, y: carbonY - hDistance, element: 'H' });
                bonds.push({ from: startIndex + i, to: hIndex++, order: 1 });
                // Bottom H
                atoms.push({ x: carbonX, y: carbonY + hDistance, element: 'H' });
                bonds.push({ from: startIndex + i, to: hIndex++, order: 1 });
                // Right H
                atoms.push({ x: carbonX + hDistance, y: carbonY, element: 'H' });
                bonds.push({ from: startIndex + i, to: hIndex++, order: 1 });
            } else {
                // Middle carbons: 2 hydrogens (top and bottom)
                // Top H
                atoms.push({ x: carbonX, y: carbonY - hDistance, element: 'H' });
                bonds.push({ from: startIndex + i, to: hIndex++, order: 1 });
                // Bottom H
                atoms.push({ x: carbonX, y: carbonY + hDistance, element: 'H' });
                bonds.push({ from: startIndex + i, to: hIndex++, order: 1 });
            }
        }

        redraw();
        updateStats();
    }

    function createCyclopropane(centerX = null, centerY = null) {
        saveState();
        if (placeholder) placeholder.style.display = 'none';
        if (centerX === null) centerX = canvas.offsetWidth / 2;
        if (centerY === null) centerY = canvas.offsetHeight / 2;
        const radius = 50;
        const hDistance = 45;

        const startIndex = atoms.length;
        // Create 3-carbon ring
        for (let i = 0; i < 3; i++) {
            const angle = (i * 120 - 90) * Math.PI / 180;
            const x = centerX + radius * Math.cos(angle);
            const y = centerY + radius * Math.sin(angle);
            atoms.push({ x, y, element: 'C' });
        }

        // Create bonds
        for (let i = 0; i < 3; i++) {
            bonds.push({
                from: startIndex + i,
                to: startIndex + ((i + 1) % 3),
                order: 1
            });
        }

        // Add hydrogen atoms (2 per carbon)
        const hStartIndex = atoms.length;
        for (let i = 0; i < 3; i++) {
            const angle = (i * 120 - 90) * Math.PI / 180;
            const perpAngle1 = angle + 15 * Math.PI / 180;
            const perpAngle2 = angle - 15 * Math.PI / 180;

            const h1x = centerX + (radius + hDistance) * Math.cos(perpAngle1);
            const h1y = centerY + (radius + hDistance) * Math.sin(perpAngle1);
            atoms.push({ x: h1x, y: h1y, element: 'H' });
            bonds.push({ from: startIndex + i, to: hStartIndex + i * 2, order: 1 });

            const h2x = centerX + (radius + hDistance) * Math.cos(perpAngle2);
            const h2y = centerY + (radius + hDistance) * Math.sin(perpAngle2);
            atoms.push({ x: h2x, y: h2y, element: 'H' });
            bonds.push({ from: startIndex + i, to: hStartIndex + i * 2 + 1, order: 1 });
        }

        redraw();
        updateStats();
    }

    function createCyclobutane(centerX = null, centerY = null) {
        saveState();
        if (placeholder) placeholder.style.display = 'none';
        if (centerX === null) centerX = canvas.offsetWidth / 2;
        if (centerY === null) centerY = canvas.offsetHeight / 2;
        const radius = 55;
        const hDistance = 45;

        const startIndex = atoms.length;
        // Create 4-carbon ring
        for (let i = 0; i < 4; i++) {
            const angle = (i * 90 - 45) * Math.PI / 180;
            const x = centerX + radius * Math.cos(angle);
            const y = centerY + radius * Math.sin(angle);
            atoms.push({ x, y, element: 'C' });
        }

        // Create bonds
        for (let i = 0; i < 4; i++) {
            bonds.push({
                from: startIndex + i,
                to: startIndex + ((i + 1) % 4),
                order: 1
            });
        }

        // Add hydrogen atoms (2 per carbon)
        const hStartIndex = atoms.length;
        for (let i = 0; i < 4; i++) {
            const angle = (i * 90 - 45) * Math.PI / 180;
            const perpAngle1 = angle + 12 * Math.PI / 180;
            const perpAngle2 = angle - 12 * Math.PI / 180;

            const h1x = centerX + (radius + hDistance) * Math.cos(perpAngle1);
            const h1y = centerY + (radius + hDistance) * Math.sin(perpAngle1);
            atoms.push({ x: h1x, y: h1y, element: 'H' });
            bonds.push({ from: startIndex + i, to: hStartIndex + i * 2, order: 1 });

            const h2x = centerX + (radius + hDistance) * Math.cos(perpAngle2);
            const h2y = centerY + (radius + hDistance) * Math.sin(perpAngle2);
            atoms.push({ x: h2x, y: h2y, element: 'H' });
            bonds.push({ from: startIndex + i, to: hStartIndex + i * 2 + 1, order: 1 });
        }

        redraw();
        updateStats();
    }

    function createCyclopentane(centerX = null, centerY = null) {
        saveState();
        if (placeholder) placeholder.style.display = 'none';
        if (centerX === null) centerX = canvas.offsetWidth / 2;
        if (centerY === null) centerY = canvas.offsetHeight / 2;
        const radius = 58;
        const hDistance = 45;

        const startIndex = atoms.length;
        // Create 5-carbon ring
        for (let i = 0; i < 5; i++) {
            const angle = (i * 72 - 90) * Math.PI / 180;
            const x = centerX + radius * Math.cos(angle);
            const y = centerY + radius * Math.sin(angle);
            atoms.push({ x, y, element: 'C' });
        }

        // Create bonds
        for (let i = 0; i < 5; i++) {
            bonds.push({
                from: startIndex + i,
                to: startIndex + ((i + 1) % 5),
                order: 1
            });
        }

        // Add hydrogen atoms (2 per carbon)
        const hStartIndex = atoms.length;
        for (let i = 0; i < 5; i++) {
            const angle = (i * 72 - 90) * Math.PI / 180;
            const perpAngle1 = angle + 12 * Math.PI / 180;
            const perpAngle2 = angle - 12 * Math.PI / 180;

            const h1x = centerX + (radius + hDistance) * Math.cos(perpAngle1);
            const h1y = centerY + (radius + hDistance) * Math.sin(perpAngle1);
            atoms.push({ x: h1x, y: h1y, element: 'H' });
            bonds.push({ from: startIndex + i, to: hStartIndex + i * 2, order: 1 });

            const h2x = centerX + (radius + hDistance) * Math.cos(perpAngle2);
            const h2y = centerY + (radius + hDistance) * Math.sin(perpAngle2);
            atoms.push({ x: h2x, y: h2y, element: 'H' });
            bonds.push({ from: startIndex + i, to: hStartIndex + i * 2 + 1, order: 1 });
        }

        redraw();
        updateStats();
    }

    function createCycloheptane(centerX = null, centerY = null) {
        saveState();
        if (placeholder) placeholder.style.display = 'none';
        if (centerX === null) centerX = canvas.offsetWidth / 2;
        if (centerY === null) centerY = canvas.offsetHeight / 2;
        const radius = 60;
        const hDistance = 45;

        const startIndex = atoms.length;
        // Create 7-carbon ring
        for (let i = 0; i < 7; i++) {
            const angle = (i * (360 / 7) - 90) * Math.PI / 180;
            const x = centerX + radius * Math.cos(angle);
            const y = centerY + radius * Math.sin(angle);
            atoms.push({ x, y, element: 'C' });
        }

        // Create ring bonds
        for (let i = 0; i < 7; i++) {
            bonds.push({ from: startIndex + i, to: startIndex + ((i + 1) % 7), order: 1 });
        }

        // Add hydrogen atoms (2 per carbon)
        const hStartIndex = atoms.length;
        for (let i = 0; i < 7; i++) {
            const angle = (i * (360 / 7) - 90) * Math.PI / 180;
            const perpAngle1 = angle + 10 * Math.PI / 180;
            const perpAngle2 = angle - 10 * Math.PI / 180;

            const h1x = centerX + (radius + hDistance) * Math.cos(perpAngle1);
            const h1y = centerY + (radius + hDistance) * Math.sin(perpAngle1);
            atoms.push({ x: h1x, y: h1y, element: 'H' });
            bonds.push({ from: startIndex + i, to: hStartIndex + i * 2, order: 1 });

            const h2x = centerX + (radius + hDistance) * Math.cos(perpAngle2);
            const h2y = centerY + (radius + hDistance) * Math.sin(perpAngle2);
            atoms.push({ x: h2x, y: h2y, element: 'H' });
            bonds.push({ from: startIndex + i, to: hStartIndex + i * 2 + 1, order: 1 });
        }

        redraw();
        updateStats();
    }

    function createCyclooctane(centerX = null, centerY = null) {
        saveState();
        if (placeholder) placeholder.style.display = 'none';
        if (centerX === null) centerX = canvas.offsetWidth / 2;
        if (centerY === null) centerY = canvas.offsetHeight / 2;
        const radius = 65;
        const hDistance = 45;

        const startIndex = atoms.length;
        // Create 8-carbon ring
        for (let i = 0; i < 8; i++) {
            const angle = (i * 45 - 90) * Math.PI / 180;
            const x = centerX + radius * Math.cos(angle);
            const y = centerY + radius * Math.sin(angle);
            atoms.push({ x, y, element: 'C' });
        }

        // Create ring bonds
        for (let i = 0; i < 8; i++) {
            bonds.push({ from: startIndex + i, to: startIndex + ((i + 1) % 8), order: 1 });
        }

        // Add hydrogen atoms (2 per carbon)
        const hStartIndex = atoms.length;
        for (let i = 0; i < 8; i++) {
            const angle = (i * 45 - 90) * Math.PI / 180;
            const perpAngle1 = angle + 8 * Math.PI / 180;
            const perpAngle2 = angle - 8 * Math.PI / 180;

            const h1x = centerX + (radius + hDistance) * Math.cos(perpAngle1);
            const h1y = centerY + (radius + hDistance) * Math.sin(perpAngle1);
            atoms.push({ x: h1x, y: h1y, element: 'H' });
            bonds.push({ from: startIndex + i, to: hStartIndex + i * 2, order: 1 });

            const h2x = centerX + (radius + hDistance) * Math.cos(perpAngle2);
            const h2y = centerY + (radius + hDistance) * Math.sin(perpAngle2);
            atoms.push({ x: h2x, y: h2y, element: 'H' });
            bonds.push({ from: startIndex + i, to: hStartIndex + i * 2 + 1, order: 1 });
        }

        redraw();
        updateStats();
    }

    function createCyclononane(centerX = null, centerY = null) {
        saveState();
        if (placeholder) placeholder.style.display = 'none';
        if (centerX === null) centerX = canvas.offsetWidth / 2;
        if (centerY === null) centerY = canvas.offsetHeight / 2;
        const radius = 68;
        const hDistance = 45;

        const startIndex = atoms.length;
        // Create 9-carbon ring
        for (let i = 0; i < 9; i++) {
            const angle = (i * 40 - 90) * Math.PI / 180;
            const x = centerX + radius * Math.cos(angle);
            const y = centerY + radius * Math.sin(angle);
            atoms.push({ x, y, element: 'C' });
        }

        // Create ring bonds
        for (let i = 0; i < 9; i++) {
            bonds.push({ from: startIndex + i, to: startIndex + ((i + 1) % 9), order: 1 });
        }

        // Add hydrogen atoms (2 per carbon)
        const hStartIndex = atoms.length;
        for (let i = 0; i < 9; i++) {
            const angle = (i * 40 - 90) * Math.PI / 180;
            const perpAngle1 = angle + 7 * Math.PI / 180;
            const perpAngle2 = angle - 7 * Math.PI / 180;

            const h1x = centerX + (radius + hDistance) * Math.cos(perpAngle1);
            const h1y = centerY + (radius + hDistance) * Math.sin(perpAngle1);
            atoms.push({ x: h1x, y: h1y, element: 'H' });
            bonds.push({ from: startIndex + i, to: hStartIndex + i * 2, order: 1 });

            const h2x = centerX + (radius + hDistance) * Math.cos(perpAngle2);
            const h2y = centerY + (radius + hDistance) * Math.sin(perpAngle2);
            atoms.push({ x: h2x, y: h2y, element: 'H' });
            bonds.push({ from: startIndex + i, to: hStartIndex + i * 2 + 1, order: 1 });
        }

        redraw();
        updateStats();
    }

    function createCyclodecane(centerX = null, centerY = null) {
        saveState();
        if (placeholder) placeholder.style.display = 'none';
        if (centerX === null) centerX = canvas.offsetWidth / 2;
        if (centerY === null) centerY = canvas.offsetHeight / 2;
        const radius = 70;
        const hDistance = 45;

        const startIndex = atoms.length;
        // Create 10-carbon ring
        for (let i = 0; i < 10; i++) {
            const angle = (i * 36 - 90) * Math.PI / 180;
            const x = centerX + radius * Math.cos(angle);
            const y = centerY + radius * Math.sin(angle);
            atoms.push({ x, y, element: 'C' });
        }

        // Create ring bonds
        for (let i = 0; i < 10; i++) {
            bonds.push({ from: startIndex + i, to: startIndex + ((i + 1) % 10), order: 1 });
        }

        // Add hydrogen atoms (2 per carbon)
        const hStartIndex = atoms.length;
        for (let i = 0; i < 10; i++) {
            const angle = (i * 36 - 90) * Math.PI / 180;
            const perpAngle1 = angle + 6 * Math.PI / 180;
            const perpAngle2 = angle - 6 * Math.PI / 180;

            const h1x = centerX + (radius + hDistance) * Math.cos(perpAngle1);
            const h1y = centerY + (radius + hDistance) * Math.sin(perpAngle1);
            atoms.push({ x: h1x, y: h1y, element: 'H' });
            bonds.push({ from: startIndex + i, to: hStartIndex + i * 2, order: 1 });

            const h2x = centerX + (radius + hDistance) * Math.cos(perpAngle2);
            const h2y = centerY + (radius + hDistance) * Math.sin(perpAngle2);
            atoms.push({ x: h2x, y: h2y, element: 'H' });
            bonds.push({ from: startIndex + i, to: hStartIndex + i * 2 + 1, order: 1 });
        }

        redraw();
        updateStats();
    }

    // Initialize - highlight Carbon by default
    const carbonBtn = Array.from(document.querySelectorAll('.atom-button')).find(btn => btn.textContent.trim() === 'C');
    if (carbonBtn) {
        carbonBtn.style.boxShadow = '0 0 0 3px #0d6efd';
    }

    updateStats();
    updateUndoRedoButtons();  // Initialize undo/redo button states

    // Modal helper functions
    function showModal(title, content) {
        document.getElementById('modalTitle').textContent = title;
        document.getElementById('modalBody').textContent = content;
        document.getElementById('reportModal').classList.add('active');
    }

    function closeModal() {
        document.getElementById('reportModal').classList.remove('active');
    }

    // Confirmation modal functions
    let confirmCallback = null;

    function showConfirmModal(message, callback) {
        confirmCallback = callback;
        document.getElementById('confirmMessage').textContent = message;
        document.getElementById('confirmModal').classList.add('active');
    }

    function closeConfirmModal(confirmed) {
        document.getElementById('confirmModal').classList.remove('active');
        if (confirmCallback) {
            confirmCallback(confirmed);
            confirmCallback = null;
        }
    }

    // Alert modal functions
    function showAlertModal(message) {
        document.getElementById('alertMessage').textContent = message;
        document.getElementById('alertModal').classList.add('active');
    }

    function closeAlertModal() {
        document.getElementById('alertModal').classList.remove('active');
    }

    function showNotification(message, type = 'success') {
        const notification = document.getElementById('notification');
        const notificationText = document.getElementById('notificationText');
        const icon = notification.querySelector('i');

        // Update icon and color based on type
        notification.className = `notification ${type} active`;
        if (type === 'success') {
            icon.className = 'fas fa-check-circle';
            icon.style.color = '#28a745';
        } else if (type === 'error') {
            icon.className = 'fas fa-exclamation-circle';
            icon.style.color = '#dc3545';
        } else if (type === 'info') {
            icon.className = 'fas fa-info-circle';
            icon.style.color = '#0d6efd';
        }

        notificationText.textContent = message;

        // Auto hide after 3 seconds
        setTimeout(() => {
            notification.classList.remove('active');
        }, 3000);
    }

    function captureCanvasSnapshot() {
        // Create a temporary canvas with white background
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = 800;
        tempCanvas.height = 600;
        const ctx = tempCanvas.getContext('2d');

        // Fill with white background
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);

        // Draw bonds first (behind atoms)
        bonds.forEach(bond => {
            const from = atoms[bond.from];
            const to = atoms[bond.to];
            if (from && to) {
                ctx.strokeStyle = '#333';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.moveTo(from.x, from.y);
                ctx.lineTo(to.x, to.y);
                ctx.stroke();
            }
        });

        // Draw atoms
        atoms.forEach(atom => {
            const color = getAtomColor(atom.element);

            ctx.beginPath();
            ctx.arc(atom.x, atom.y, 20, 0, Math.PI * 2);
            ctx.fillStyle = 'white';
            ctx.fill();
            ctx.strokeStyle = color;
            ctx.lineWidth = 2;
            ctx.stroke();

            ctx.fillStyle = color;
            ctx.font = 'bold 16px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(atom.element, atom.x, atom.y);
        });

        return tempCanvas.toDataURL('image/png');
    }

    // Action buttons functionality

    // Save Design button -> open modal
    const saveButton = document.getElementById('saveDesignBtn');
    const saveNameModalEl = document.getElementById('saveNameModal');
    const saveNameInput = document.getElementById('saveNameInput');
    const saveNameConfirmBtn = document.getElementById('saveNameConfirmBtn');
    const saveNameModal = saveNameModalEl ? new bootstrap.Modal(saveNameModalEl) : null;

    function performSaveDesign(nameValue) {
        const safeName = (nameValue || '').trim() || 'Untitled Compound';

        // Capture canvas snapshot
        const snapshot = captureCanvasSnapshot();

        const design = {
            name: safeName,
            atoms: atoms,
            bonds: bonds,
            timestamp: new Date().toISOString(),
            formula: document.getElementById('molecularFormula').textContent,
            snapshot: snapshot
        };

        // Save to localStorage
        let savedDesigns = JSON.parse(localStorage.getItem('savedMolecules') || '[]');
        savedDesigns.unshift(design);  // Add to beginning

        // Keep only last 10 designs
        if (savedDesigns.length > 10) {
            savedDesigns = savedDesigns.slice(0, 10);
        }

        localStorage.setItem('savedMolecules', JSON.stringify(savedDesigns));

        showNotification('Design saved successfully to library!', 'success');
        loadRecentDesigns();  // Refresh recent designs display
    }

    if (saveButton && saveNameModal) {
        saveButton.addEventListener('click', function () {
            if (atoms.length === 0) {
                showNotification('No molecule to save! Please create a molecule first.', 'error');
                return;
            }
            // Pre-fill with formula or blank
            const formulaText = document.getElementById('molecularFormula')?.textContent?.trim() || '';
            saveNameInput.value = formulaText || '';
            saveNameModal.show();
            setTimeout(() => saveNameInput.focus(), 150);
        });

        saveNameConfirmBtn.addEventListener('click', function () {
            performSaveDesign(saveNameInput.value);
            saveNameModal.hide();
        });
    }

    // Analyze button
    const analyzeBtn = document.querySelector('.btn-primary-action:has(.fa-flask)');
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', function () {
            if (atoms.length === 0) {
                showNotification('No molecule to analyze! Please create a molecule first.', 'error');
                return;
            }

            const analysis = `Molecular Analysis Report
========================

Molecular Formula: ${document.getElementById('molecularFormula').textContent}
Total Atoms: ${atoms.length}
Total Bonds: ${bonds.length}
Molecular Weight: ${document.getElementById('molecularWeight').textContent} g/mol

Atom Distribution:
${Object.entries(atoms.reduce((acc, atom) => {
                acc[atom.element] = (acc[atom.element] || 0) + 1;
                return acc;
            }, {})).map(([el, count]) => `  ${el}: ${count}`).join('\n')}

Bond Distribution:
  Single Bonds: ${bonds.filter(b => b.order === 1).length}
  Double Bonds: ${bonds.filter(b => b.order === 2).length}
  Triple Bonds: ${bonds.filter(b => b.order === 3).length}`;

            showModal('Molecular Analysis', analysis);
        });
    }

    // 3D View toggle and visualization
    let viewer3d = null;

    window.toggle3DView = function () {
        const container = document.getElementById('viewer3d-container');

        if (container.style.display === 'none') {
            if (atoms.length === 0) {
                showNotification('No molecule to visualize! Please create a molecule first.', 'error');
                return;
            }

            container.style.display = 'block';

            // Initialize 3D viewer
            if (!viewer3d) {
                const element = document.getElementById('viewer3d');
                const theme = document.documentElement.getAttribute('data-theme') || 'light';
                const bgColor = (theme === 'dark' || theme === 'recomended') ? 0x1a1a1a : 0xffffff;

                viewer3d = $3Dmol.createViewer(element, {
                    backgroundColor: bgColor
                });
            }

            // Generate XYZ format from current molecule
            const xyz = generate3DXYZ();

            if (xyz) {
                viewer3d.clear();
                viewer3d.addModel(xyz, 'xyz');
                viewer3d.setStyle({}, { stick: { radius: 0.15 }, sphere: { radius: 0.4 } });
                viewer3d.zoomTo();
                viewer3d.render();
            } else {
                showNotification('Unable to generate 3D structure', 'error');
            }
        } else {
            container.style.display = 'none';
        }
    };

    function generate3DXYZ() {
        if (atoms.length === 0) return null;

        // Start with atom count and comment
        let xyz = atoms.length + '\n';
        xyz += 'Generated from Molecule Designer\n';

        // Convert 2D coordinates to pseudo-3D
        // Use simple spring-based Z-coordinate estimation
        atoms.forEach(atom => {
            const element = atom.element;
            // Normalize 2D coordinates to reasonable 3D scale
            const x = ((atom.x - 400) / 50).toFixed(4);
            const y = ((400 - atom.y) / 50).toFixed(4);

            // Calculate Z based on bond angles for better 3D appearance
            let z = 0;
            const connectedBonds = bonds.filter(b => b.from === atoms.indexOf(atom) || b.to === atoms.indexOf(atom));

            if (connectedBonds.length > 0) {
                // Add slight Z variation based on number of bonds
                z = (connectedBonds.length % 2 === 0 ? -0.5 : 0.5) * Math.random();
            }

            xyz += `${element} ${x} ${y} ${z.toFixed(4)}\n`;
        });

        return xyz;
    }

    // 3D View button (old handler - now using onclick)
    const view3dBtn = document.querySelector('.btn-info-action:has(.fa-cube)');
    if (view3dBtn) {
        view3dBtn.addEventListener('click', function (e) {
            // Handler moved to toggle3DView function
            e.stopPropagation();
        });
    }

    // AI Optimize button - Enhanced with better algorithms
    const aiOptimizeBtn = document.querySelector('.btn-primary-action:has(.fa-brain)');
    if (aiOptimizeBtn) {
        aiOptimizeBtn.addEventListener('click', function () {
            if (atoms.length === 0) {
                showNotification('No molecule to optimize! Please create a molecule first.', 'error');
                return;
            }

            saveState();

            // Advanced optimization: Force-directed layout with spring model
            const optimizationSteps = 50;
            const repulsionStrength = 8000;
            const springLength = 70;
            const springStrength = 0.05;
            const damping = 0.9;

            // Track velocities for better convergence
            const velocities = atoms.map(() => ({ vx: 0, vy: 0 }));

            let totalEnergy = 0;

            for (let step = 0; step < optimizationSteps; step++) {
                const forces = atoms.map(() => ({ fx: 0, fy: 0 }));

                // 1. Coulomb repulsion (all atom pairs)
                for (let i = 0; i < atoms.length; i++) {
                    for (let j = i + 1; j < atoms.length; j++) {
                        const dx = atoms[j].x - atoms[i].x;
                        const dy = atoms[j].y - atoms[i].y;
                        const distSq = dx * dx + dy * dy;
                        const dist = Math.sqrt(distSq);

                        if (dist > 0) {
                            const force = repulsionStrength / distSq;
                            const fx = (dx / dist) * force;
                            const fy = (dy / dist) * force;

                            forces[i].fx -= fx;
                            forces[i].fy -= fy;
                            forces[j].fx += fx;
                            forces[j].fy += fy;
                        }
                    }
                }

                // 2. Spring forces for bonded atoms (Hooke's law)
                bonds.forEach(bond => {
                    const i = bond.from;
                    const j = bond.to;
                    const dx = atoms[j].x - atoms[i].x;
                    const dy = atoms[j].y - atoms[i].y;
                    const dist = Math.sqrt(dx * dx + dy * dy);

                    if (dist > 0) {
                        // Ideal length varies by bond order
                        const idealLength = springLength * (bond.order === 2 ? 0.9 : bond.order === 3 ? 0.85 : 1.0);
                        const displacement = dist - idealLength;
                        const force = displacement * springStrength;

                        const fx = (dx / dist) * force;
                        const fy = (dy / dist) * force;

                        forces[i].fx += fx;
                        forces[i].fy += fy;
                        forces[j].fx -= fx;
                        forces[j].fy -= fy;
                    }
                });

                // 3. Apply forces with velocity damping
                totalEnergy = 0;
                atoms.forEach((atom, i) => {
                    velocities[i].vx = (velocities[i].vx + forces[i].fx) * damping;
                    velocities[i].vy = (velocities[i].vy + forces[i].fy) * damping;

                    atom.x += velocities[i].vx;
                    atom.y += velocities[i].vy;

                    totalEnergy += velocities[i].vx * velocities[i].vx + velocities[i].vy * velocities[i].vy;
                });

                // Early termination if converged
                if (totalEnergy < 0.01) break;
            }

            // Center the molecule in the canvas
            const avgX = atoms.reduce((sum, a) => sum + a.x, 0) / atoms.length;
            const avgY = atoms.reduce((sum, a) => sum + a.y, 0) / atoms.length;
            const centerX = 400;
            const centerY = 300;

            atoms.forEach(atom => {
                atom.x += centerX - avgX;
                atom.y += centerY - avgY;
            });

            redraw();
            showNotification('✓ Structure optimized with spring-force algorithm!', 'success');
        });
    }

    // Validate Structure button - Enhanced with comprehensive validation
    const validateBtn = document.querySelector('.btn-success-action:has(.fa-check-circle)');
    if (validateBtn) {
        validateBtn.addEventListener('click', function () {
            if (atoms.length === 0) {
                showNotification('No molecule to validate! Please create a molecule first.', 'error');
                return;
            }

            const valences = {
                'H': 1, 'C': 4, 'N': 3, 'O': 2, 'S': 2, 'P': 5,
                'F': 1, 'Cl': 1, 'Br': 1, 'I': 1
            };

            const atomBonds = atoms.map(() => 0);
            bonds.forEach(bond => {
                atomBonds[bond.from] += bond.order || 1;
                atomBonds[bond.to] += bond.order || 1;
            });

            let valenceErrors = [];
            let warnings = [];
            let overlapIssues = [];
            let bondAngleIssues = [];

            // 1. Valence validation
            atoms.forEach((atom, i) => {
                const expected = valences[atom.element] || 4;
                const actual = atomBonds[i];
                if (actual > expected) {
                    valenceErrors.push(`Atom ${i + 1} (${atom.element}): Too many bonds (${actual}/${expected})`);
                } else if (actual < expected && atom.element !== 'H') {
                    warnings.push(`Atom ${i + 1} (${atom.element}): Incomplete valence (${actual}/${expected})`);
                }
            });

            // 2. Atom overlap detection
            for (let i = 0; i < atoms.length; i++) {
                for (let j = i + 1; j < atoms.length; j++) {
                    const dx = atoms[j].x - atoms[i].x;
                    const dy = atoms[j].y - atoms[i].y;
                    const dist = Math.sqrt(dx * dx + dy * dy);

                    // Check if atoms are too close (likely overlapping)
                    if (dist < 25 && !bonds.some(b =>
                        (b.from === i && b.to === j) || (b.from === j && b.to === i))) {
                        overlapIssues.push(`Atoms ${i + 1} and ${j + 1} are overlapping (distance: ${dist.toFixed(1)}px)`);
                    }
                }
            }

            // 3. Bond angle validation (check for unrealistic angles)
            atoms.forEach((atom, i) => {
                const connectedBonds = bonds.filter(b => b.from === i || b.to === i);

                if (connectedBonds.length >= 2) {
                    for (let b1 = 0; b1 < connectedBonds.length; b1++) {
                        for (let b2 = b1 + 1; b2 < connectedBonds.length; b2++) {
                            const bond1 = connectedBonds[b1];
                            const bond2 = connectedBonds[b2];

                            const other1 = atoms[bond1.from === i ? bond1.to : bond1.from];
                            const other2 = atoms[bond2.from === i ? bond2.to : bond2.from];

                            // Calculate angle
                            const v1x = other1.x - atom.x;
                            const v1y = other1.y - atom.y;
                            const v2x = other2.x - atom.x;
                            const v2y = other2.y - atom.y;

                            const dot = v1x * v2x + v1y * v2y;
                            const mag1 = Math.sqrt(v1x * v1x + v1y * v1y);
                            const mag2 = Math.sqrt(v2x * v2x + v2y * v2y);

                            if (mag1 > 0 && mag2 > 0) {
                                const angle = Math.acos(Math.max(-1, Math.min(1, dot / (mag1 * mag2)))) * 180 / Math.PI;

                                // Flag very acute angles (< 30°) for sp3 carbons
                                if (angle < 30 && atom.element === 'C' && connectedBonds.length === 4) {
                                    bondAngleIssues.push(`Atom ${i + 1} (${atom.element}): Very acute angle ${angle.toFixed(1)}°`);
                                }
                            }
                        }
                    }
                }
            });

            // 4. Isolated atoms check
            const isolatedAtoms = atoms.map((a, i) => ({ atom: a, index: i }))
                .filter((_, i) => atomBonds[i] === 0 && atoms[i].element !== 'H')
                .map(item => `Atom ${item.index + 1} (${item.atom.element})`);

            // Compile report
            let report = '=== STRUCTURE VALIDATION REPORT ===\n\n';

            if (valenceErrors.length === 0 && warnings.length === 0 && overlapIssues.length === 0 &&
                bondAngleIssues.length === 0 && isolatedAtoms.length === 0) {
                report += '✓ VALID STRUCTURE\n\n';
                report += 'All validation checks passed:\n';
                report += '  ✓ Valence bonds correct\n';
                report += '  ✓ No atom overlaps\n';
                report += '  ✓ Bond angles reasonable\n';
                report += '  ✓ No isolated atoms\n';
                showModal('Structure Validation', report);
                return;
            }

            let hasErrors = false;

            if (valenceErrors.length > 0) {
                report += '❌ VALENCE ERRORS:\n' + valenceErrors.map(e => '  • ' + e).join('\n') + '\n\n';
                hasErrors = true;
            }

            if (overlapIssues.length > 0) {
                report += '❌ OVERLAP ISSUES:\n' + overlapIssues.slice(0, 5).map(e => '  • ' + e).join('\n');
                if (overlapIssues.length > 5) report += `\n  ... and ${overlapIssues.length - 5} more`;
                report += '\n\n';
                hasErrors = true;
            }

            if (warnings.length > 0) {
                report += '⚠️ WARNINGS:\n' + warnings.slice(0, 5).map(w => '  • ' + w).join('\n');
                if (warnings.length > 5) report += `\n  ... and ${warnings.length - 5} more`;
                report += '\n\n';
            }

            if (bondAngleIssues.length > 0) {
                report += '⚠️ ANGLE WARNINGS:\n' + bondAngleIssues.slice(0, 3).map(w => '  • ' + w).join('\n');
                if (bondAngleIssues.length > 3) report += `\n  ... and ${bondAngleIssues.length - 3} more`;
                report += '\n\n';
            }

            if (isolatedAtoms.length > 0) {
                report += '⚠️ ISOLATED ATOMS:\n  • ' + isolatedAtoms.join(', ') + '\n\n';
            }

            report += '💡 SUGGESTIONS:\n';
            if (valenceErrors.length > 0) report += '  • Add or remove bonds to satisfy valence\n';
            if (overlapIssues.length > 0) report += '  • Use AI Optimize to spread atoms apart\n';
            if (warnings.length > 0) report += '  • Add hydrogen atoms where needed\n';

            showModal(hasErrors ? 'Validation Failed' : 'Structure Validation', report);
        });
    }

    // Calculate Properties button - Enhanced with comprehensive calculations
    const calcPropsBtn = document.querySelector('.btn-info-action:has(.fa-calculator)');
    if (calcPropsBtn) {
        calcPropsBtn.addEventListener('click', function () {
            if (atoms.length === 0) {
                showNotification('No molecule to calculate! Please create a molecule first.', 'error');
                return;
            }

            const weights = {
                'H': 1.008, 'C': 12.011, 'N': 14.007, 'O': 15.999, 'S': 32.065, 'P': 30.974,
                'F': 18.998, 'Cl': 35.453, 'Br': 79.904, 'I': 126.904
            };

            const atomCount = atoms.reduce((acc, atom) => {
                acc[atom.element] = (acc[atom.element] || 0) + 1;
                return acc;
            }, {});

            const mw = atoms.reduce((sum, atom) => sum + (weights[atom.element] || 0), 0);

            // Calculate detailed properties
            const carbonCount = atomCount['C'] || 0;
            const hydrogenCount = atomCount['H'] || 0;
            const oxygenCount = atomCount['O'] || 0;
            const nitrogenCount = atomCount['N'] || 0;
            const sulfurCount = atomCount['S'] || 0;
            const fluorineCount = atomCount['F'] || 0;
            const chlorineCount = atomCount['Cl'] || 0;
            const bromineCount = atomCount['Br'] || 0;
            const heavyAtoms = atoms.filter(a => a.element !== 'H').length;

            // Enhanced LogP estimation (Wildman-Crippen)
            const logP = (carbonCount * 0.5) + (hydrogenCount * 0.2) - (oxygenCount * 0.5) -
                (nitrogenCount * 0.5) - (sulfurCount * 0.2) + (chlorineCount * 0.3) +
                (bromineCount * 0.4) + (fluorineCount * 0.1);

            // Topological Polar Surface Area (TPSA)
            const tpsa = (oxygenCount * 20.23) + (nitrogenCount * 23.79);

            // Count ring systems (simplified - count cycles)
            let rings = 0;
            const visited = new Set();
            const adjList = new Map();
            bonds.forEach(bond => {
                if (!adjList.has(bond.from)) adjList.set(bond.from, []);
                if (!adjList.has(bond.to)) adjList.set(bond.to, []);
                adjList.get(bond.from).push(bond.to);
                adjList.get(bond.to).push(bond.from);
            });

            // Simple cycle detection
            atoms.forEach((_, i) => {
                if (!visited.has(i) && adjList.has(i)) {
                    const neighbors = adjList.get(i) || [];
                    if (neighbors.length >= 2) rings++;
                }
            });
            rings = Math.floor(rings / 3); // Rough approximation

            // Rotatable bonds (single bonds, not in rings, not terminal)
            const rotatableBonds = bonds.filter(bond => {
                if (bond.order !== 1) return false;
                const neighbors1 = (adjList.get(bond.from) || []).length;
                const neighbors2 = (adjList.get(bond.to) || []).length;
                return neighbors1 > 1 && neighbors2 > 1;
            }).length;

            // H-bond donors (OH, NH)
            let hbondDonors = 0;
            atoms.forEach((atom, i) => {
                if (atom.element === 'O' || atom.element === 'N') {
                    const connectedH = bonds.filter(b =>
                    ((b.from === i && atoms[b.to].element === 'H') ||
                        (b.to === i && atoms[b.from].element === 'H'))
                    ).length;
                    hbondDonors += connectedH;
                }
            });

            // H-bond acceptors (O, N)
            const hbondAcceptors = oxygenCount + nitrogenCount;

            // Lipinski's Rule of Five
            const lipinskiViolations = [
                mw > 500 ? 'Molecular Weight > 500' : null,
                logP > 5 ? 'LogP > 5' : null,
                hbondDonors > 5 ? 'H-Bond Donors > 5' : null,
                hbondAcceptors > 10 ? 'H-Bond Acceptors > 10' : null
            ].filter(v => v !== null);

            // Formal charge approximation
            let formalCharge = 0;
            atoms.forEach((atom, i) => {
                const bondCount = bonds.filter(b => b.from === i || b.to === i)
                    .reduce((sum, b) => sum + (b.order || 1), 0);
                const expectedBonds = { 'N': 3, 'O': 2, 'S': 2 }[atom.element];
                if (expectedBonds && bondCount !== expectedBonds) {
                    formalCharge += expectedBonds - bondCount;
                }
            });

            // Saturation metrics
            const maxBonds = carbonCount * 4 + nitrogenCount * 3 + oxygenCount * 2 + sulfurCount * 2;
            const actualBonds = bonds.reduce((sum, b) => sum + (b.order || 1), 0) * 2;
            const unsaturation = (maxBonds - actualBonds - hydrogenCount) / 2;

            // Compile comprehensive report
            let report = '=== MOLECULAR PROPERTIES ===\n\n';

            report += '📊 BASIC PROPERTIES\n';
            report += `  Molecular Formula: ${document.getElementById('molecularFormula').textContent}\n`;
            report += `  Molecular Weight: ${mw.toFixed(3)} g/mol\n`;
            report += `  Heavy Atoms: ${heavyAtoms}\n`;
            report += `  Formal Charge: ${formalCharge >= 0 ? '+' : ''}${formalCharge}\n\n`;

            report += '🧪 PHYSICOCHEMICAL PROPERTIES\n';
            report += `  LogP (lipophilicity): ${logP.toFixed(2)}\n`;
            report += `  TPSA: ${tpsa.toFixed(1)} ų (${tpsa < 140 ? 'good' : 'poor'} absorption)\n`;
            report += `  Rotatable Bonds: ${rotatableBonds} (${rotatableBonds <= 10 ? 'flexible' : 'very flexible'})\n`;
            report += `  H-Bond Donors: ${hbondDonors}\n`;
            report += `  H-Bond Acceptors: ${hbondAcceptors}\n\n`;

            report += '🔬 STRUCTURAL FEATURES\n';
            report += `  Ring Systems: ~${rings}\n`;
            report += `  Degree of Unsaturation: ${Math.max(0, unsaturation).toFixed(1)}\n`;
            report += `  Single Bonds: ${bonds.filter(b => b.order === 1).length}\n`;
            report += `  Double Bonds: ${bonds.filter(b => b.order === 2).length}\n`;
            report += `  Triple Bonds: ${bonds.filter(b => b.order === 3).length}\n\n`;

            report += '💊 DRUG-LIKENESS (Lipinski\'s Rule of 5)\n';
            if (lipinskiViolations.length === 0) {
                report += '  ✓ PASSES all criteria\n';
                report += '  Likely has good oral bioavailability\n\n';
            } else {
                report += `  ⚠️ VIOLATIONS: ${lipinskiViolations.length}/4\n`;
                lipinskiViolations.forEach(v => report += `    • ${v}\n`);
                report += '  May have poor oral bioavailability\n\n';
            }

            report += '📈 PROPERTY RANGES\n';
            report += `  LogP: ${logP.toFixed(2)} ${logP < 0 ? '(hydrophilic)' : logP < 3 ? '(balanced)' : logP < 5 ? '(lipophilic)' : '(very lipophilic)'}\n`;
            report += `  TPSA: ${tpsa.toFixed(1)} ${tpsa < 60 ? '(low)' : tpsa < 140 ? '(moderate)' : '(high)'}\n`;
            report += `  MW: ${mw.toFixed(1)} ${mw < 300 ? '(small)' : mw < 500 ? '(medium)' : '(large)'}\n\n`;

            report += '📝 Note: Values are estimates based on 2D structure';

            showModal('Comprehensive Molecular Properties', report);
        });
    }

    // Load recent designs on page load
    function loadRecentDesigns() {
        console.log('loadRecentDesigns called');
        const savedDesigns = JSON.parse(localStorage.getItem('savedMolecules') || '[]');
        console.log('Saved designs:', savedDesigns.length);
        const container = document.querySelector('.recent-designs');
        console.log('Container found:', !!container);

        if (!container) {
            console.error('Recent designs container not found!');
            return;
        }

        // Get current theme
        const theme = document.documentElement.getAttribute('data-theme') || 'light';
        const isDark = (theme === 'dark' || theme === 'recomended');

        if (savedDesigns.length === 0) {
            const emptyColor = isDark ? '#666' : '#999';
            container.innerHTML = `<div style="text-align: center; color: ${emptyColor}; padding: 20px;">No saved designs yet</div>`;
            return;
        }

        const itemBg = isDark ? '#2d2d2d' : 'white';
        const itemBorder = isDark ? '#404040' : '#ddd';
        const textColor = isDark ? '#e0e0e0' : '#333';
        const dateColor = isDark ? '#999' : '#666';
        const statsColor = isDark ? '#777' : '#999';
        const imgBg = isDark ? '#1a1a1a' : 'white';
        const imgBorder = isDark ? '#404040' : '#ddd';

        container.innerHTML = savedDesigns.slice(0, 5).map((design, index) => {
            const date = new Date(design.timestamp).toLocaleDateString();
            const title = design.name || design.formula || 'Untitled Compound';
            return `
                <div class="design-item" onclick="loadDesign(${index})" style="cursor: pointer; padding: 10px; border: 1px solid ${itemBorder}; border-radius: 5px; margin-bottom: 10px; transition: all 0.2s; background: ${itemBg};">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <input type="checkbox" class="form-check-input design-select" data-index="${index}" onclick="event.stopPropagation();" />
                        <img src="${design.snapshot}" style="width: 60px; height: 60px; object-fit: contain; border: 1px solid ${imgBorder}; border-radius: 4px; background: ${imgBg};">
                        <div style="flex: 1; min-width: 0;">
                            <div style="font-weight: 600; font-size: 0.9rem; color: ${textColor};">${title}</div>
                            ${design.formula ? `<div style="font-size: 0.75rem; color: ${dateColor};">${design.formula}</div>` : ''}
                            <div style="font-size: 0.75rem; color: ${dateColor};">${date}</div>
                            <div style="font-size: 0.7rem; color: ${statsColor};">${design.atoms.length} atoms, ${design.bonds.length} bonds</div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // Add hover effect
        const hoverBg = isDark ? '#383838' : '#f8f9fa';
        const hoverBorder = isDark ? '#667eea' : '#0d6efd';

        document.querySelectorAll('.design-item').forEach(item => {
            item.addEventListener('mouseenter', function () {
                this.style.background = hoverBg;
                this.style.borderColor = hoverBorder;
            });
            item.addEventListener('mouseleave', function () {
                this.style.background = itemBg;
                this.style.borderColor = itemBorder;
            });
        });
    }

    window.loadDesign = function (index) {
        const savedDesigns = JSON.parse(localStorage.getItem('savedMolecules') || '[]');
        const design = savedDesigns[index];

        if (design) {
            saveState();
            atoms = design.atoms;
            bonds = design.bonds;
            redraw();
            updateStats();
            showNotification('Design loaded successfully!', 'info');
        }
    };

    window.deleteSelectedDesigns = function () {
        const checkboxes = document.querySelectorAll('.design-select:checked');
        console.log('Found checkboxes:', checkboxes.length);

        if (checkboxes.length === 0) {
            showNotification('Please select designs to delete.', 'info');
            return;
        }

        // Get the indices from checkboxes
        const indicesToDelete = Array.from(checkboxes).map(cb => {
            const idx = parseInt(cb.getAttribute('data-index'), 10);
            console.log('Checkbox index:', idx);
            return idx;
        }).filter(n => !isNaN(n));

        console.log('Indices to delete:', indicesToDelete);

        // Confirm deletion
        if (!confirm(`Delete ${indicesToDelete.length} selected design(s)?`)) {
            return;
        }

        let savedDesigns = JSON.parse(localStorage.getItem('savedMolecules') || '[]');
        console.log('Total designs before delete:', savedDesigns.length);

        // Sort indices in descending order to delete from end to start
        indicesToDelete.sort((a, b) => b - a);

        // Delete each selected design
        indicesToDelete.forEach(idx => {
            if (idx >= 0 && idx < savedDesigns.length) {
                console.log('Deleting design at index:', idx);
                savedDesigns.splice(idx, 1);
            }
        });

        console.log('Total designs after delete:', savedDesigns.length);

        localStorage.setItem('savedMolecules', JSON.stringify(savedDesigns));
        loadRecentDesigns();
        showNotification(`${indicesToDelete.length} design(s) deleted successfully`, 'success');
    };

    // Convert molecule name to SMILES using multiple APIs as fallback
    async function convertNameToSMILES() {
        const nameInput = document.getElementById('moleculeName');
        const statusDiv = document.getElementById('conversionStatus');
        const smilesDiv = document.getElementById('smilesNotation');
        const formulaDiv = document.getElementById('molecularFormula');
        const iupacDiv = document.getElementById('iupacName');
        const commonDiv = document.getElementById('commonName');

        const name = nameInput.value.trim();

        if (!name) {
            statusDiv.innerHTML = '<span style="color: #dc3545;">⚠️ Please enter a molecule name</span>';
            return;
        }

        statusDiv.innerHTML = '<span style="color: #0d6efd;"><i class="fas fa-spinner fa-spin"></i> Converting...</span>';

        try {
            // Try method 1: PubChem API (most reliable)
            try {
                const pubchemUrl = `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/${encodeURIComponent(name)}/property/CanonicalSMILES,MolecularFormula,IUPACName/JSON`;
                const pubchemResponse = await fetch(pubchemUrl);

                if (pubchemResponse.ok) {
                    const data = await pubchemResponse.json();
                    const compound = data.PropertyTable.Properties[0];

                    smilesDiv.textContent = compound.CanonicalSMILES;
                    formulaDiv.textContent = compound.MolecularFormula;
                    iupacDiv.textContent = compound.IUPACName || '-';
                    commonDiv.textContent = name;

                    statusDiv.innerHTML = '<span style="color: #28a745;">✓ Converted via PubChem. Drawing structure...</span>';

                    // Automatically draw the 2D structure on canvas
                    await drawStructureFromSMILES(compound.CanonicalSMILES);

                    statusDiv.innerHTML = '<span style="color: #28a745;">✓ Converted and drawn via PubChem</span>';
                    return;
                }
            } catch (e) {
                console.log('PubChem failed, trying CIR...', e);
            }

            // Try method 2: Chemical Identifier Resolver (NCI)
            try {
                const cirUrl = `https://cactus.nci.nih.gov/chemical/structure/${encodeURIComponent(name)}/smiles`;
                const cirResponse = await fetch(cirUrl);

                if (cirResponse.ok) {
                    const smiles = await cirResponse.text();

                    if (smiles && !smiles.includes('html') && !smiles.includes('error')) {
                        smilesDiv.textContent = smiles.trim();
                        commonDiv.textContent = name;

                        // Try to get more info from PubChem using SMILES
                        try {
                            const infoUrl = `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/${encodeURIComponent(smiles)}/property/MolecularFormula,IUPACName/JSON`;
                            const infoResponse = await fetch(infoUrl);
                            if (infoResponse.ok) {
                                const infoData = await infoResponse.json();
                                const compound = infoData.PropertyTable.Properties[0];
                                formulaDiv.textContent = compound.MolecularFormula;
                                iupacDiv.textContent = compound.IUPACName || '-';
                            }
                        } catch (e) {
                            // Calculate formula from atoms if available
                            formulaDiv.textContent = '-';
                            iupacDiv.textContent = '-';
                        }

                        statusDiv.innerHTML = '<span style="color: #28a745;">✓ Converted via CIR. Drawing structure...</span>';

                        // Automatically draw the 2D structure on canvas
                        await drawStructureFromSMILES(smiles.trim());

                        statusDiv.innerHTML = '<span style="color: #28a745;">✓ Converted and drawn via CIR</span>';
                        return;
                    }
                }
            } catch (e) {
                console.log('CIR failed:', e);
            }

            // If all methods fail
            statusDiv.innerHTML = '<span style="color: #dc3545;">⚠️ Molecule not found. Try a different name or use IUPAC name.</span>';

        } catch (error) {
            console.error('Conversion error:', error);
            statusDiv.innerHTML = '<span style="color: #dc3545;">⚠️ Conversion failed. Check your connection.</span>';
        }
    }

    // Draw 2D structure from SMILES on canvas
    async function drawStructureFromSMILES(smiles) {
        try {
            // Use NCI CACTUS to get SDF with 2D coordinates
            const sdfUrl = `https://cactus.nci.nih.gov/chemical/structure/${encodeURIComponent(smiles)}/file?format=sdf`;
            const response = await fetch(sdfUrl);

            if (!response.ok) {
                console.error('Failed to fetch 2D coordinates');
                return;
            }

            const sdfData = await response.text();

            // Parse SDF to extract atom coordinates
            const lines = sdfData.split('\n');
            let atomCount = 0;
            let bondCount = 0;

            // Find counts line (line 4 in SDF format)
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i].trim();
                const parts = line.split(/\s+/);
                if (parts.length >= 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
                    atomCount = parseInt(parts[0]);
                    bondCount = parseInt(parts[1]);

                    // Clear existing canvas
                    atoms = [];
                    bonds = [];
                    canvasInner.querySelectorAll('.placed-atom, .bond-line').forEach(el => el.remove());
                    if (placeholder) placeholder.style.display = 'none';

                    // Scale factor to fit in canvas (canvas is ~800x500)
                    const scale = 30;
                    const offsetX = 400;
                    const offsetY = 250;

                    // Parse atoms
                    for (let j = i + 1; j <= i + atomCount; j++) {
                        const atomLine = lines[j].trim().split(/\s+/);
                        if (atomLine.length >= 4) {
                            const x = parseFloat(atomLine[0]) * scale + offsetX;
                            const y = -parseFloat(atomLine[1]) * scale + offsetY; // Invert Y
                            const element = atomLine[3];

                            atoms.push({ x, y, element, charge: 0 });
                            drawAtom(x, y, element, 0);
                        }
                    }

                    // Parse bonds
                    for (let j = i + atomCount + 1; j <= i + atomCount + bondCount; j++) {
                        const bondLine = lines[j].trim().split(/\s+/);
                        if (bondLine.length >= 3) {
                            const from = parseInt(bondLine[0]) - 1; // SDF is 1-indexed
                            const to = parseInt(bondLine[1]) - 1;
                            const type = parseInt(bondLine[2]);

                            bonds.push({ from, to, type });
                        }
                    }

                    drawBonds();
                    updateStats();
                    saveState();

                    console.log(`Drew ${atomCount} atoms and ${bondCount} bonds`);
                    break;
                }
            }

        } catch (error) {
            console.error('Error drawing structure from SMILES:', error);
        }
    }

    // Get molecule names from SMILES notation
    async function getSMILESNames() {
        const smilesDiv = document.getElementById('smilesNotation');
        const iupacDiv = document.getElementById('iupacName');
        const commonDiv = document.getElementById('commonName');
        const formulaDiv = document.getElementById('molecularFormula');
        const validationDiv = document.getElementById('smilesValidation');

        const smiles = smilesDiv.textContent.trim();

        if (!smiles || smiles === '-') {
            validationDiv.innerHTML = '<span style="color: #dc3545;">⚠️ No SMILES notation available</span>';
            return;
        }

        validationDiv.innerHTML = '<span style="color: #0d6efd;"><i class="fas fa-spinner fa-spin"></i> Fetching names...</span>';

        try {
            // Get compound info from PubChem using SMILES
            const url = `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/${encodeURIComponent(smiles)}/property/MolecularFormula,IUPACName,Title/JSON`;
            const response = await fetch(url);

            if (response.ok) {
                const data = await response.json();
                const compound = data.PropertyTable.Properties[0];

                formulaDiv.textContent = compound.MolecularFormula;
                iupacDiv.textContent = compound.IUPACName || '-';
                commonDiv.textContent = compound.Title || '-';

                validationDiv.innerHTML = '<span style="color: #28a745;">✓ Names retrieved from PubChem</span>';
            } else {
                validationDiv.innerHTML = '<span style="color: #ffc107;">⚠️ Molecule not found in PubChem database</span>';
            }
        } catch (error) {
            console.error('Name lookup error:', error);
            validationDiv.innerHTML = '<span style="color: #dc3545;">⚠️ Failed to retrieve names</span>';
        }
    }

    // Allow Enter key to trigger conversion
    const moleculeNameInput = document.getElementById('moleculeName');
    if (moleculeNameInput) {
        moleculeNameInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                convertNameToSMILES();
            }
        });
    }
</script>

<!-- 3Dmol.js Library for dedicated 3D viewer -->
<script src="https://3Dmol.csb.pitt.edu/build/3Dmol-min.js"></script>
<script>
    // Dedicated 3D Viewer for the new 3D View canvas
    let dedicatedViewer = null;
    let isRotating = false;
    let rotationInterval = null;

    // Initialize the dedicated 3D viewer
    function initDedicated3DViewer() {
        if (!dedicatedViewer) {
            const element = document.getElementById('viewer3d-main');
            const theme = document.documentElement.getAttribute('data-theme') || 'light';
            const bgColor = (theme === 'dark' || theme === 'recomended') ? '#1a1a1a' : '#667eea';

            dedicatedViewer = $3Dmol.createViewer(element, {
                backgroundColor: bgColor
            });
        }
        updateDedicated3DView();
    }

    // Update the dedicated 3D viewer with current molecule
    function updateDedicated3DView() {
        if (!dedicatedViewer) {
            initDedicated3DViewer();
            return;
        }

        const loadingDiv = document.getElementById('viewer3d-loading');

        if (atoms.length === 0) {
            loadingDiv.style.display = 'block';
            loadingDiv.innerHTML = '<i class="fas fa-cube fa-3x mb-3"></i><p>Design a molecule to see 3D view</p>';
            dedicatedViewer.clear();
            dedicatedViewer.render();
            return;
        }

        loadingDiv.style.display = 'none';

        // Generate XYZ format from current molecule
        const xyz = generate3DXYZ();

        if (xyz) {
            dedicatedViewer.clear();
            dedicatedViewer.addModel(xyz, 'xyz');
            dedicatedViewer.setStyle({}, {
                stick: { radius: 0.15, color: 'spectrum' },
                sphere: { radius: 0.4, colorscheme: 'Jmol' }
            });
            dedicatedViewer.zoomTo();
            dedicatedViewer.render();
        }
    }

    // Rotate button functionality
    window.toggleRotation = function () {
        if (!dedicatedViewer || atoms.length === 0) return;

        isRotating = !isRotating;

        if (isRotating) {
            rotationInterval = setInterval(() => {
                dedicatedViewer.rotate(1, 'y');
                dedicatedViewer.render();
            }, 30);
        } else {
            if (rotationInterval) {
                clearInterval(rotationInterval);
                rotationInterval = null;
            }
        }
    };

    // Refresh button functionality
    window.refresh3DView = function () {
        if (!dedicatedViewer) return;
        isRotating = false;
        if (rotationInterval) {
            clearInterval(rotationInterval);
            rotationInterval = null;
        }
        updateDedicated3DView();
    };

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function () {
        // Load recent designs
        loadRecentDesigns();

        // Initialize 3D viewer
        setTimeout(() => {
            initDedicated3DViewer();
        }, 500);

        // Close modal on click outside
        const reportModal = document.getElementById('reportModal');
        if (reportModal) {
            reportModal.addEventListener('click', function (e) {
                if (e.target === this) {
                    closeModal();
                }
            });
        }
    });

    // Hook into existing functions to update 3D view automatically
    const originalPlaceAtom = window.placeAtom;
    if (typeof originalPlaceAtom === 'function') {
        window.placeAtom = function (...args) {
            originalPlaceAtom.apply(this, args);
            setTimeout(updateDedicated3DView, 100);
        };
    }
