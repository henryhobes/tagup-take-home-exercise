// Every click on the board loads a new page, which would jump back to the top of the fleet list.
// This keeps the list where it was. Everything still works without it (DECISIONS.md A13).
const KEY = "board-scroll";
// A different search is a different list, so an offset saved for another one means nothing here.
const search = new URLSearchParams(location.search).get("q") ?? "";
const board = document.querySelector(".board");
const boardVisible = () => getComputedStyle(board).display !== "none";

if (boardVisible()) {
  // After an action the URL points at the changed write-up. Beside the board, only the panel
  // should move to it; letting the browser follow the anchor would scroll the board too.
  const card = location.hash && document.querySelector(location.hash);
  if (card) history.replaceState(null, "", location.pathname + location.search);

  const saved = JSON.parse(sessionStorage.getItem(KEY));
  if (saved && saved.search === search) window.scrollTo(0, saved.y);
  if (card) card.scrollIntoView({ block: "nearest" });
}

addEventListener("pagehide", () => {
  if (boardVisible()) sessionStorage.setItem(KEY, JSON.stringify({ search, y: window.scrollY }));
});
