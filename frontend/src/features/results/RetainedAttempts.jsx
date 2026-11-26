import React, { useState } from "react";
import { Cell, Column, Row, Table, TableBody, TableHeader } from "react-aria-components/Table";

const pageSize = 10;

export default function RetainedAttempts({ attempts, onTrace }) {
  const [sort, setSort] = useState({ column: "attempt", direction: "ascending" });
  const [page, setPage] = useState(0);
  const pageIndex = Math.min(page, Math.max(0, Math.ceil(attempts.length / pageSize) - 1));
  const start = pageIndex * pageSize;
  const end = Math.min(start + pageSize, attempts.length);
  const direction = sort.direction === "ascending" ? 1 : -1;
  const sorted = attempts.toSorted((first, second) => direction * (first.attempt - second.attempt));

  if (!attempts.length) return <p>No retained attempts for this selection.</p>;

  return (
    <>
      <Table
        aria-labelledby="group-attempts-heading"
        className="retained-attempts-table"
        sortDescriptor={sort}
        onSortChange={(descriptor) => {
          setSort(descriptor);
          setPage(0);
        }}
      >
        <TableHeader>
          <Column id="attempt" isRowHeader allowsSorting>
            {({ sortDirection }) => (
              <>Attempt <span aria-hidden="true">{sortDirection === "ascending" ? "↑" : "↓"}</span></>
            )}
          </Column>
          <Column>Status</Column>
          <Column>Trace</Column>
        </TableHeader>
        <TableBody>
          {sorted.slice(start, end).map((attempt) => (
            <Row key={attempt.attempt} id={attempt.attempt}>
              <Cell>
                <strong>{attempt.attempt}</strong>
                <small>Repeat {attempt.repeat} · {attempt.condition}</small>
              </Cell>
              <Cell>
                <span>{attempt.status || "No saved result"}</span>
                {attempt.execution_time_ms != null && <small>{Math.round(attempt.execution_time_ms)} ms</small>}
                {attempt.error_category && <small>{attempt.error_category}</small>}
              </Cell>
              <Cell>
                {attempt.run_id ? (
                  <a
                    href={`/results/runs/${attempt.run_id}`}
                    aria-label={`View trace · Attempt ${attempt.attempt} · EXP-${String(attempt.run_id).padStart(3, "0")}`}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") event.stopPropagation();
                    }}
                    onClick={(event) => {
                      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
                      event.preventDefault();
                      onTrace(attempt.run_id);
                    }}
                  >
                    View trace
                    <small>EXP-{String(attempt.run_id).padStart(3, "0")}</small>
                  </a>
                ) : (
                  <small>Trace unavailable</small>
                )}
              </Cell>
            </Row>
          ))}
        </TableBody>
      </Table>
      {attempts.length > pageSize && (
        <div className="retained-attempts-pagination">
          <button type="button" className="text-button" aria-disabled={start === 0}
            onClick={() => start > 0 && setPage(pageIndex - 1)}>
            Previous page
          </button>
          <span role="status">{start + 1}–{end} of {attempts.length} attempts</span>
          <button type="button" className="text-button" aria-disabled={end === attempts.length}
            onClick={() => end < attempts.length && setPage(pageIndex + 1)}>
            Next page
          </button>
        </div>
      )}
    </>
  );
}
