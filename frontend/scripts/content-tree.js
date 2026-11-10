const clone = (value) => structuredClone(value);

function isRecord(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function findPath(nodes, id) {
  if (!Array.isArray(nodes)) return null;
  const path = [];
  const walk = (list) => {
    for (let index = 0; index < list.length; index += 1) {
      const node = list[index];
      if (!isRecord(node)) continue;
      path.push({ node, index });
      if (node.id === id) return true;
      if (Array.isArray(node.children) && walk(node.children)) return true;
      path.pop();
    }
    return false;
  };
  return walk(nodes) ? path : null;
}

function locationFrom(path) {
  const parent = path.length > 1 ? path[path.length - 2].node : null;
  return {
    parentId: parent ? parent.id : null,
    index: path[path.length - 1].index,
  };
}

function childCount(nodes, parentId) {
  if (parentId === null) return nodes.length;
  const path = findPath(nodes, parentId);
  if (!path) return null;
  const children = path[path.length - 1].node.children;
  return Array.isArray(children) ? children.length : 0;
}

// Index in the destination list. Values outside [0, length] are clamped.
function clampIndex(index, length) {
  const value = Number(index);
  if (!Number.isFinite(value)) return length;
  return Math.min(length, Math.max(0, Math.trunc(value)));
}

// Mutates `nodes`, which must already be a private clone.
function place(nodes, parentId, index, node) {
  const list = parentId === null ? nodes : (() => {
    const path = findPath(nodes, parentId);
    const parent = path[path.length - 1].node;
    if (!Array.isArray(parent.children)) parent.children = [];
    return parent.children;
  })();
  list.splice(index, 0, node);
}

/** Location of `id`. Root nodes use `parentId === null`. First match wins. */
export function findLocation(nodes, id) {
  const path = findPath(nodes, id);
  return path ? locationFrom(path) : null;
}

/** True when `nodeId` is `ancestorId` or sits inside its subtree. */
export function contains(nodes, ancestorId, nodeId) {
  const path = findPath(nodes, nodeId);
  return Boolean(path && path.some((step) => step.node.id === ancestorId));
}

/** Insert a deep copy of `node`. `parentId === null` inserts at the root. */
export function insertNode(nodes, parentId, index, node) {
  if (!Array.isArray(nodes) || !isRecord(node)) return nodes;
  const length = childCount(nodes, parentId);
  if (length === null) return nodes;
  const next = clone(nodes);
  place(next, parentId, clampIndex(index, length), clone(node));
  return next;
}

/**
 * Move the node, keeping its id, props, and children.
 * `index` is its index in the destination parent after the move.
 * A move into the node itself or into its descendant returns `nodes`.
 */
export function moveNode(nodes, nodeId, parentId, index) {
  if (!Array.isArray(nodes)) return nodes;
  const sourcePath = findPath(nodes, nodeId);
  if (!sourcePath) return nodes;
  if (parentId !== null && contains(nodes, nodeId, parentId)) return nodes;
  const length = childCount(nodes, parentId);
  if (length === null) return nodes;
  const source = locationFrom(sourcePath);
  const sameParent = source.parentId === parentId;
  const destination = clampIndex(index, length - (sameParent ? 1 : 0));
  if (sameParent && destination === source.index) return nodes;

  const next = clone(nodes);
  const from = source.parentId === null ? next : (() => {
    const path = findPath(next, source.parentId);
    return path[path.length - 1].node.children;
  })();
  const [moved] = from.splice(source.index, 1);
  place(next, parentId, destination, moved);
  return next;
}

/**
 * Copy props and children, assign a new id to every copied node, and insert
 * the copy immediately after the original. `makeId` is called with no
 * arguments, parent before children.
 */
export function duplicateNode(nodes, nodeId, makeId) {
  if (!Array.isArray(nodes)) return nodes;
  const sourcePath = findPath(nodes, nodeId);
  if (!sourcePath) return nodes;
  const source = locationFrom(sourcePath);

  const copyTree = (node) => {
    if (!isRecord(node)) return clone(node);
    const copy = clone(node);
    copy.id = makeId();
    if (Array.isArray(node.children)) {
      copy.children = node.children.map((child) => copyTree(child));
    }
    return copy;
  };

  const next = clone(nodes);
  const originalPath = findPath(next, nodeId);
  const original = originalPath[originalPath.length - 1].node;
  place(next, source.parentId, source.index + 1, copyTree(original));
  return next;
}

/** Remove the node and its children. An empty root is valid. */
export function removeNode(nodes, nodeId) {
  if (!Array.isArray(nodes)) return nodes;
  const sourcePath = findPath(nodes, nodeId);
  if (!sourcePath) return nodes;
  const source = locationFrom(sourcePath);
  const next = clone(nodes);
  const list = source.parentId === null ? next : (() => {
    const path = findPath(next, source.parentId);
    return path[path.length - 1].node.children;
  })();
  list.splice(source.index, 1);
  return next;
}

/**
 * Section that should receive a new element: the selected section, otherwise
 * the nearest section ancestor, otherwise the last root section, otherwise null.
 */
export function sectionIdFor(nodes, selectedId) {
  if (selectedId !== undefined && selectedId !== null) {
    const path = findPath(nodes, selectedId);
    if (path) {
      for (let index = path.length - 1; index >= 0; index -= 1) {
        if (path[index].node.type === "section") return path[index].node.id;
      }
    }
  }
  if (!Array.isArray(nodes)) return null;
  for (let index = nodes.length - 1; index >= 0; index -= 1) {
    if (isRecord(nodes[index]) && nodes[index].type === "section") return nodes[index].id;
  }
  return null;
}
