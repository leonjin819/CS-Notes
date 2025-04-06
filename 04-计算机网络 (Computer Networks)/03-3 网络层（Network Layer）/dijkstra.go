package main

import (
	"container/heap"
	"fmt"
	"math"
)

// Graph 表示一个带权重的图
// 使用邻接表表示: map[节点名]map[邻居节点名]权重
type Graph map[string]map[string]int

// pqItem 是优先队列中的元素
type pqItem struct {
	node     string // 节点名称
	priority int    // 从源节点到此节点的当前最短距离 (用作优先级)
	index    int    // 元素在堆中的索引 (由 heap.Interface 管理)
}

// priorityQueue 实现了 heap.Interface 接口，是一个基于 pqItem 的最小堆
type priorityQueue []*pqItem

// Len 返回队列长度
func (pq priorityQueue) Len() int { return len(pq) }

// Less 比较两个元素的优先级，用于维持最小堆性质 (距离越小优先级越高)
func (pq priorityQueue) Less(i, j int) bool {
	return pq[i].priority < pq[j].priority
}

// Swap 交换两个元素在堆中的位置
func (pq priorityQueue) Swap(i, j int) {
	pq[i], pq[j] = pq[j], pq[i]
	pq[i].index = i
	pq[j].index = j
}

// Push 向队列中添加一个元素
func (pq *priorityQueue) Push(x interface{}) {
	n := len(*pq)
	item := x.(*pqItem)
	item.index = n
	*pq = append(*pq, item)
}

// Pop 从队列中移除并返回优先级最高(距离最小)的元素
func (pq *priorityQueue) Pop() interface{} {
	old := *pq
	n := len(old)
	item := old[n-1]
	old[n-1] = nil  // 避免内存泄漏
	item.index = -1 // 表示元素已不在堆中
	*pq = old[0 : n-1]
	return item
}

// update 修改队列中某个元素的优先级和值
// 注意：这个标准库的 heap 实现不直接支持高效的 "decrease-key" 操作。
// 一个常见的解决方法是直接将带有新优先级的项 Push 进堆，
// 并在 Pop 时检查取出的项是否是“过时”的（即其距离大于已记录的最短距离）。
// 这个实现采用了这种简化策略。
// 如果需要严格的 O(log n) decrease-key，需要更复杂的实现或使用支持该操作的库。

// Dijkstra 算法实现
// 输入: 图 graph 和起始节点 startNode
// 输出:
//   - distances: 从 startNode 到所有其他节点的最短距离 map
//   - previous: 用于重建最短路径的 map (previous[节点] = 最短路径上的前一个节点)
func Dijkstra(graph Graph, startNode string) (distances map[string]int, previous map[string]string) {
	distances = make(map[string]int)
	previous = make(map[string]string)
	pq := make(priorityQueue, 0)
	nodeItems := make(map[string]*pqItem) // 用于快速查找节点在队列中的项

	// 1. 初始化
	for node := range graph {
		distances[node] = math.MaxInt64 // 所有距离初始化为无穷大
		previous[node] = ""             // 前驱节点初始化为空
	}

	// 起始节点的距离为 0
	if _, ok := graph[startNode]; !ok {
		fmt.Printf("起始节点 '%s' 不在图中\n", startNode)
		return distances, previous // 或者返回错误
	}
	distances[startNode] = 0

	// 将起始节点加入优先队列
	startItem := &pqItem{node: startNode, priority: 0}
	heap.Push(&pq, startItem)
	nodeItems[startNode] = startItem

	// 2. 主循环
	for pq.Len() > 0 {
		// 取出当前距离最小的节点 u
		currentItem := heap.Pop(&pq).(*pqItem)
		u := currentItem.node

		// 优化：如果取出的项的距离比已记录的距离大，说明它是“过时的”
		// (因为我们可能已经通过更短的路径更新了该节点的距离并 push 了新的项)
		if currentItem.priority > distances[u] {
			continue
		}

		// 遍历节点 u 的所有邻居 v
		if neighbors, ok := graph[u]; ok {
			for v, weight := range neighbors {
				// 计算通过 u 到达 v 的距离
				altDistance := distances[u] + weight

				// 如果找到了更短的路径
				if altDistance < distances[v] {
					distances[v] = altDistance
					previous[v] = u

					// 将更新后的节点 v (或新的 v 项) 加入/更新到优先队列
					// 使用简化的策略：直接 Push 新项
					newItem := &pqItem{node: v, priority: altDistance}
					heap.Push(&pq, newItem)
					nodeItems[v] = newItem // 更新映射 (如果需要精确更新会更复杂)
				}
			}
		}
	}

	return distances, previous
}

// GetPath 使用 previous map 重建从 startNode 到 endNode 的最短路径
func GetPath(previous map[string]string, startNode, endNode string) ([]string, bool) {
	path := []string{}
	curr := endNode

	// 从终点回溯到起点
	for curr != "" {
		path = append([]string{curr}, path...) // 在路径前面添加节点
		if curr == startNode {
			return path, true // 找到完整路径
		}
		prev, ok := previous[curr]
		if !ok {
			// 如果 endNode 不可达，或者 startNode 不存在于 previous 的链中
			return nil, false
		}
		curr = prev
	}

	// 如果 curr 变为空但还没到 startNode (只有当 endNode == startNode 且 startNode 不在图中时可能发生?)
	// 或者 endNode 本身就不可达 (循环一开始 curr 就在 previous 中找不到)
	if len(path) == 0 || path[0] != startNode {
		return nil, false // 无法构建路径或路径不完整
	}

	// 理论上，如果 Dijkstra 正确运行且 endNode 可达，上面的 return path, true 应该能捕捉到
	return path, true // 应该不会执行到这里
}

func main() {
	// 示例图
	graph := Graph{
		"A": {"B": 1, "C": 4},
		"B": {"A": 1, "C": 2, "D": 5},
		"C": {"A": 4, "B": 2, "D": 1},
		"D": {"B": 5, "C": 1, "E": 3},
		"E": {"D": 3},
		"F": {}, // 一个孤立节点
	}

	start := "A"
	distances, previous := Dijkstra(graph, start)

	fmt.Printf("从节点 %s 出发的最短距离:\n", start)
	for node, dist := range distances {
		if dist == math.MaxInt64 {
			fmt.Printf("  到 %s: 无穷大 (不可达)\n", node)
		} else {
			fmt.Printf("  到 %s: %d\n", node, dist)
		}
	}

	fmt.Println("\n最短路径示例:")
	target := "E"
	path, found := GetPath(previous, start, target)
	if found {
		fmt.Printf("  从 %s 到 %s 的最短路径: %v\n", start, target, path)
	} else {
		fmt.Printf("  从 %s 无法到达 %s\n", start, target)
	}

	target = "F"
	path, found = GetPath(previous, start, target)
	if found {
		fmt.Printf("  从 %s 到 %s 的最短路径: %v\n", start, target, path) // 不会打印，因为 F 不可达
	} else {
		fmt.Printf("  从 %s 无法到达 %s\n", start, target)
	}

	target = "A"
	path, found = GetPath(previous, start, target)
	if found {
		fmt.Printf("  从 %s 到 %s 的最短路径: %v\n", start, target, path)
	} else {
		fmt.Printf("  从 %s 无法到达 %s\n", start, target)
	}
}
