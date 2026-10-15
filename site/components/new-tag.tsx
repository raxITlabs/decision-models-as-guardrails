/** "New" after the name of a system that joined the board after the first release. Not a pill: a pulsing dot and a
 *  small-caps word, accent blue on paper and a lighter blue over a painting (styles in globals.css, .new-tag). */
export function NewTag({ onArt = false }: { onArt?: boolean }) {
  return (
    <span className={onArt ? "new-tag new-tag-art" : "new-tag"}>
      <span aria-hidden="true" className="new-tag-dot" />
      New
    </span>
  );
}
