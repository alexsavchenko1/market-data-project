package main

import (
	"fmt"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"
)

const chartPath = "/v8/finance/chart/"

var (
	attempts      = make(map[string]int)
	attemptsMutex sync.Mutex
)

func main() {
	http.HandleFunc(chartPath, handleChart)

	log.Println("Симулятор запущен: http://localhost:8080")

	log.Fatal(
		http.ListenAndServe(":8080", nil),
	)
}

func handleChart(
	writer http.ResponseWriter,
	request *http.Request,
) {
	ticker := strings.TrimPrefix(
		request.URL.Path,
		chartPath,
	)
	ticker = strings.ToUpper(
		strings.TrimSpace(ticker),
	)

	if ticker == "" {
		http.NotFound(writer, request)
		return
	}

	attemptsMutex.Lock()
	attempts[ticker]++
	attempt := attempts[ticker]
	attemptsMutex.Unlock()

	log.Printf(
		"ticker=%s attempt=%d",
		ticker,
		attempt,
	)

	if strings.HasPrefix(ticker, "SLOW") {
		time.Sleep(time.Second)
	}

	switch ticker {
	case "FLAKY":
		if attempt <= 2 {
			http.Error(
				writer,
				"Временная ошибка",
				http.StatusServiceUnavailable,
			)
			return
		}

	case "RATE":
		if attempt <= 2 {
			http.Error(
				writer,
				"Превышен лимит запросов",
				http.StatusTooManyRequests,
			)
			return
		}

	case "FAIL":
		http.Error(
			writer,
			"Поставщик недоступен",
			http.StatusServiceUnavailable,
		)
		return
	}

	writer.Header().Set(
		"Content-Type",
		"application/json",
	)

	_, _ = fmt.Fprintf(
		writer,
		`{
			"chart": {
				"result": [{
					"meta": {
						"currency": "USD",
						"symbol": %q
					},
					"timestamp": [
						1735776000,
						1735862400,
						1736121600,
						1736208000,
						1736294400
					],
					"indicators": {
						"adjclose": [{
							"adjclose": [
								100,
								102,
								99,
								104,
								101
							]
						}]
					}
				}],
				"error": null
			}
		}`,
		ticker,
	)
}
