import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ecocycle_ai/core/app_state.dart';
import 'package:ecocycle_ai/screens/add_item_screen.dart';
import 'package:ecocycle_ai/screens/circular_marketplace_screen.dart';
import 'package:ecocycle_ai/screens/marketplace_browse_screen.dart';

void main() {
  testWidgets('Screen 6: Landing renders exactly two primary options & Future Scope',
      (WidgetTester tester) async {
    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: CircularMarketplaceScreen(appState: appState),
    ));

    // Verify Title and Subtitle
    expect(find.text('Circular Marketplace'), findsOneWidget);
    expect(find.text('Give items a second life'), findsOneWidget);

    // Verify Exactly Two Primary Options
    expect(find.text('Add Item'), findsOneWidget);
    expect(find.text('Purchase Item'), findsOneWidget);

    // Verify Future Scope section & 3 concepts
    expect(find.text('Future Scope'), findsOneWidget);
    expect(find.text('B2B — Business to Business'), findsOneWidget);
    expect(find.textContaining('packaging company supplies reusable cardboard'), findsOneWidget);

    expect(find.text('P2P — Peer to Peer'), findsOneWidget);
    expect(find.textContaining('An old study table is offered to a nearby resident'), findsOneWidget);

    expect(find.text('NGO Connections'), findsOneWidget);
    expect(find.textContaining('NGO collects reusable clothes'), findsOneWidget);
  });

  testWidgets('Screen 6 Landing -> Add Item & Purchase Item navigation',
      (WidgetTester tester) async {
    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: CircularMarketplaceScreen(appState: appState),
    ));

    // Tap Add Item option
    await tester.tap(find.text('Add Item'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // Verify we navigated to AddItemScreen
    expect(find.byType(AddItemScreen), findsOneWidget);
    expect(find.text('Enter item name'), findsOneWidget);

    // Pop back to landing
    await tester.tap(find.byIcon(Icons.arrow_back_ios_new_rounded).last);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // Tap Purchase Item option
    await tester.tap(find.text('Purchase Item'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // Verify we navigated to MarketplaceBrowseScreen
    expect(find.byType(MarketplaceBrowseScreen), findsOneWidget);
    expect(find.text('Search items...'), findsOneWidget);
  });

  testWidgets('Screen 7: AddItemScreen renders all form fields and Sell/Give Away toggle',
      (WidgetTester tester) async {
    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: AddItemScreen(appState: appState),
    ));

    // Verify Header
    expect(find.text('Add Item'), findsNWidgets(2)); // AppBar title & CTA button
    expect(find.text('Circular Marketplace'), findsOneWidget);

    // Verify Toggle
    expect(find.text('Sell'), findsOneWidget);
    expect(find.text('Give Away'), findsOneWidget);

    // Verify Form Fields
    expect(find.text('Item Name'), findsOneWidget);
    expect(find.text('Category'), findsOneWidget);
    expect(find.text('Condition'), findsOneWidget);
    expect(find.text('Price (optional)'), findsOneWidget);
    expect(find.text('Add Photos (optional)'), findsOneWidget);
    expect(find.text('Tap to add photos'), findsOneWidget);

    // Tap "Give Away" toggle -> Price field should be hidden
    await tester.tap(find.text('Give Away'));
    await tester.pump();
    expect(find.text('Price (optional)'), findsNothing);

    // Tap "Sell" toggle -> Price field restored
    await tester.tap(find.text('Sell'));
    await tester.pump();
    expect(find.text('Price (optional)'), findsOneWidget);

    // Tap photo box -> attaches photo
    await tester.tap(find.text('Tap to add photos'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('Photograph Attached'), findsOneWidget);
  });

  testWidgets('Screen 6 Browse: MarketplaceBrowseScreen renders search, filter pills & items',
      (WidgetTester tester) async {
    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: MarketplaceBrowseScreen(appState: appState),
    ));

    // Verify Header
    expect(find.text('Circular Marketplace'), findsOneWidget);
    expect(find.text('Give items a second life'), findsOneWidget);

    // Verify Filter Pills
    expect(find.text('All'), findsOneWidget);
    expect(find.text('Sell'), findsWidgets);
    expect(find.text('Give Away'), findsWidgets);

    // Verify Search Bar
    expect(find.text('Search items...'), findsOneWidget);

    // Verify reference items matching Screen 6
    expect(find.text('Used Books'), findsOneWidget);
    expect(find.text('Cloth Bags'), findsOneWidget);
    expect(find.text('Plastic Containers'), findsOneWidget);
    expect(find.text('Furniture (Chair)'), findsOneWidget);
  });
}
